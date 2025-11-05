"""安全的Python代码执行器 - 基础设施

提供全局沙盒容器管理和抽象基类，供各节点实现自己的执行器。
各节点的具体执行器实现应放在对应的节点目录下。
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, TypeVar, Generic
import atexit

try:
    from llm_sandbox import SandboxSession
    import docker
    HAS_SANDBOX = True
except ImportError:
    HAS_SANDBOX = False


# 泛型类型
T_Input = TypeVar('T_Input')
T_Output = TypeVar('T_Output')


class GlobalSandboxContainer:
    """全局单例沙盒容器管理器
    
    用于管理一个持久化的Docker容器，避免每次执行时重新创建容器的开销。
    在首次使用时自动创建容器，程序退出时自动清理。
    
    Example:
        >>> container_id = GlobalSandboxContainer.get_container_id()
        >>> # 在 SandboxSession 中使用
        >>> with SandboxSession(container_id=container_id, lang="python") as session:
        ...     result = session.run(code)
    """
    
    _instance = None
    _container = None
    _container_id = None
    _docker_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_container_id(cls, image: str = "ghcr.io/vndee/sandbox-python-311-bullseye") -> str:
        """获取全局容器ID，如果不存在则创建
        
        Args:
            image: Docker镜像名称
            
        Returns:
            容器ID
            
        Raises:
            RuntimeError: Docker服务不可用或容器创建失败
        """
        if cls._container_id is not None:
            # 检查容器是否仍然存在
            try:
                if cls._docker_client is None:
                    cls._docker_client = docker.from_env()
                container = cls._docker_client.containers.get(cls._container_id)
                # 确保容器在运行
                if container.status != "running":
                    container.start()
                return cls._container_id
            except docker.errors.NotFound:
                # 容器已被删除，重新创建
                cls._container_id = None
                cls._container = None
        
        # 创建新容器
        try:
            if cls._docker_client is None:
                cls._docker_client = docker.from_env()
            
            # 尝试使用固定名称，如果已存在则删除旧的
            container_name = "deepeye-sandbox-persistent"
            try:
                old_container = cls._docker_client.containers.get(container_name)
                old_container.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            # 创建新容器
            cls._container = cls._docker_client.containers.run(
                image,
                detach=True,
                tty=True,
                stdin_open=True,
                name=container_name,
                remove=False  # 不自动删除，由我们管理生命周期
            )
            cls._container_id = cls._container.id
            
            # 注册退出时清理
            atexit.register(cls.cleanup)
            
            return cls._container_id
            
        except Exception as e:
            raise RuntimeError(f"无法创建全局沙盒容器: {type(e).__name__}: {e}")
    
    @classmethod
    def cleanup(cls):
        """清理全局容器"""
        if cls._container is not None:
            try:
                cls._container.stop()
                cls._container.remove()
            except Exception:
                pass  # 忽略清理错误
            finally:
                cls._container = None
                cls._container_id = None
        
        if cls._docker_client is not None:
            try:
                cls._docker_client.close()
            except Exception:
                pass
            finally:
                cls._docker_client = None
    
    @classmethod
    def reset(cls):
        """重置容器（强制重新创建）"""
        cls.cleanup()
        cls._container_id = None


class BaseCodeExecutor(ABC, Generic[T_Input, T_Output]):
    """代码执行器抽象基类
    
    定义了代码执行的通用流程，子类可以定制：
    - 输入数据的准备和注入
    - 输出结果的提取和解析
    - 所需的库列表
    
    Example:
        >>> # 子类实现
        >>> class MyExecutor(BaseCodeExecutor[dict, str]):
        ...     def _prepare_code(self, code, context):
        ...         return f"data = {context}\\n{code}"
        ...     
        ...     def _extract_result(self, output):
        ...         return output.strip()
        >>> 
        >>> executor = MyExecutor(libraries=["pandas"])
        >>> success, result, error = executor.execute("result = data['key']", {"key": "value"})
    """
    
    def __init__(
        self,
        timeout: int = 30,
        libraries: Optional[List[str]] = None,
        verbose: bool = False
    ):
        """初始化代码执行器
        
        Args:
            timeout: 执行超时时间（秒）
            libraries: 需要的Python库列表
            verbose: 是否输出详细信息
        
        Raises:
            ImportError: 未安装llm-sandbox
        """
        if not HAS_SANDBOX:
            raise ImportError(
                "使用CodeExecutor需要安装llm-sandbox:\n"
                "  uv pip install 'llm-sandbox[docker]'\n"
                "  或: pip install 'llm-sandbox[docker]'"
            )
        
        self.timeout = timeout
        self.libraries = libraries or []
        self.verbose = verbose
    
    @abstractmethod
    def _prepare_code(self, code: str, context: T_Input) -> str:
        """准备要执行的代码
        
        子类需要实现此方法，将输入上下文注入到代码中
        
        Args:
            code: 用户提供的代码
            context: 输入上下文（类型由子类定义）
        
        Returns:
            完整的可执行代码
        
        Example:
            >>> def _prepare_code(self, code, df):
            ...     # 序列化df并注入
            ...     return f"df = load_dataframe()\\n{code}"
        """
        pass
    
    @abstractmethod
    def _extract_result(self, output: str) -> T_Output:
        """从输出中提取结果
        
        子类需要实现此方法，从沙盒的stdout中提取结果
        
        Args:
            output: 沙盒执行的stdout输出
        
        Returns:
            提取的结果（类型由子类定义）
        
        Example:
            >>> def _extract_result(self, output):
            ...     # 从输出中解析DataFrame
            ...     return parse_dataframe(output)
        """
        pass
    
    def _finalize_result(self, session: 'SandboxSession', preliminary_result: T_Output) -> T_Output:
        """在提取结果后进行最终处理（可选的钩子方法）
        
        子类可以重写此方法来做额外的后处理，比如从沙盒复制文件等。
        默认实现直接返回preliminary_result。
        
        Args:
            session: 当前的SandboxSession对象，可用于文件操作等
            preliminary_result: _extract_result返回的初步结果
        
        Returns:
            最终结果
        
        Example:
            >>> def _finalize_result(self, session, preliminary_result):
            ...     # 从沙盒复制文件到本地
            ...     for item in preliminary_result:
            ...         session.copy_from_runtime(item['path'], local_path)
            ...     return preliminary_result
        """
        return preliminary_result
    
    def execute(
        self,
        code: str,
        context: T_Input,
        additional_libraries: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[T_Output], Optional[str]]:
        """执行代码（通用流程）
        
        Args:
            code: 要执行的Python代码
            context: 输入上下文
            additional_libraries: 额外需要的库
        
        Returns:
            (是否成功, 结果/None, 错误信息/None)
        """
        try:
            # 1. 准备代码
            full_code = self._prepare_code(code, context)
            
            # 2. 合并库列表
            all_libraries = list(set(
                self.libraries + (additional_libraries or [])
            ))
            
            # 3. 获取全局容器并执行代码
            container_id = GlobalSandboxContainer.get_container_id()
            with SandboxSession(
                lang="python",
                container_id=container_id,
                verbose=self.verbose,
                execution_timeout=self.timeout
            ) as session:
                result = session.run(full_code, libraries=all_libraries)
                
                # 4. 检查错误
                if result.exit_code != 0:
                    return False, None, f"代码执行错误:\n{result.stderr}"
                
                # 5. 提取结果
                try:
                    preliminary_result = self._extract_result(result.stdout)
                except Exception as e:
                    return False, None, f"结果提取失败: {type(e).__name__}: {e}"
                
                # 6. 最终处理（允许子类访问session进行文件操作等）
                try:
                    extracted_result = self._finalize_result(session, preliminary_result)
                except Exception as e:
                    return False, None, f"结果处理失败: {type(e).__name__}: {e}"
            
            return True, extracted_result, None
        
        except Exception as e:
            return False, None, f"沙盒执行异常: {type(e).__name__}: {e}"
