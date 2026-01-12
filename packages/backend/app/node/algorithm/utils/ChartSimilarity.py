from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import os

class ChartSimilarity:
    """
    使用CLIP模型计算图表相似度的工具类
    """
    def __init__(self):
        """初始化CLIP模型和处理器"""
        try:
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.initialized = True
            print("✅ CLIP模型加载成功，可用于图表相似度检测")
        except Exception as e:
            print(f"⚠️ CLIP模型加载失败: {str(e)}")
            self.initialized = False

    def get_image_embedding(self, img_path):
        """
        计算图片的嵌入向量
        
        参数:
            img_path: 图像文件路径
            
        返回:
            图像的嵌入向量
        """
        if not self.initialized:
            return None
            
        try:
            # 打开并转换图像
            img = Image.open(img_path).convert("RGB")
            
            # 处理图像并获取特征
            inputs = self.processor(images=img, return_tensors="pt")
            with torch.no_grad():
                features = self.model.get_image_features(**inputs)
            
            # L2归一化
            return features / features.norm(dim=-1, keepdim=True)
        except Exception as e:
            print(f"⚠️ 计算图像嵌入失败: {str(e)}")
            return None

    def calculate_similarity(self, img_path1, img_path2):
        """
        计算两个图像之间的相似度
        
        参数:
            img_path1: 第一个图像文件路径
            img_path2: 第二个图像文件路径
            
        返回:
            余弦相似度值，范围在-1到1之间
        """
        if not self.initialized:
            return 0.0
            
        try:
            # 获取两个图像的嵌入向量
            embedding1 = self.get_image_embedding(img_path1)
            embedding2 = self.get_image_embedding(img_path2)
            
            if embedding1 is None or embedding2 is None:
                return 0.0
            
            # 计算余弦相似度
            similarity = torch.nn.functional.cosine_similarity(embedding1, embedding2).item()
            return similarity
        except Exception as e:
            print(f"⚠️ 计算图表相似度时出错: {str(e)}")
            return 0.0
    
    def batch_compare(self, new_img_path, existing_img_paths, threshold=0.85):
        """
        一次性高效计算一个新图表与多个已有图表的相似度
        
        参数:
            new_img_path: 新图像的文件路径
            existing_img_paths: 现有图像的文件路径列表
            threshold: 相似度阈值，超过此值则认为图像相似
            
        返回:
            (is_similar, similarity, similar_img_path, all_similarities) 元组:
            - is_similar: 布尔值，表示是否找到相似图像
            - similarity: 最高相似度值
            - similar_img_path: 最相似图像的路径
            - all_similarities: 字典，键为图片路径，值为相似度
        """
        if not self.initialized or not existing_img_paths:
            return False, 0.0, None, {}
            
        try:
            # 获取新图像的嵌入向量
            new_embedding = self.get_image_embedding(new_img_path)
            if new_embedding is None:
                return False, 0.0, None, {}
            
            max_similarity = 0.0
            most_similar_path = None
            all_similarities = {}
            
            # 一次性加载并处理所有已有图表的嵌入向量
            for path in existing_img_paths:
                try:
                    existing_embedding = self.get_image_embedding(path)
                    if existing_embedding is None:
                        continue
                    
                    # 计算余弦相似度
                    similarity = torch.nn.functional.cosine_similarity(new_embedding, existing_embedding).item()
                    all_similarities[path] = similarity
                    
                    if similarity > max_similarity:
                        max_similarity = similarity
                        most_similar_path = path
                except Exception as e:
                    print(f"⚠️ 处理图表 {path} 时出错: {str(e)}")
                    continue
            
            # 如果相似度超过阈值，认为图像相似
            is_similar = max_similarity > threshold
            
            return is_similar, max_similarity, most_similar_path, all_similarities
        except Exception as e:
            print(f"⚠️ 批量比较图表相似度时出错: {str(e)}")
            return False, 0.0, None, {}


# 使用示例
if __name__ == "__main__":
    similarity_tool = ChartSimilarity()
    
    # 测试两个图表的相似度
    img1 = "/path/to/chart1.png"  # 替换为实际路径
    img2 = "/path/to/chart2.png"  # 替换为实际路径
    
    if os.path.exists(img1) and os.path.exists(img2):
        similarity = similarity_tool.calculate_similarity(img1, img2)
        print(f"图表相似度（cosine similarity）: {round(similarity, 4)}")
    else:
        print("示例图表路径不存在，请替换为有效路径进行测试")