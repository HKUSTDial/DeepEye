# 音频生成失败诊断指南

## 问题现象
生成的视频配置文件中，所有场景的 `time_range` 都是 `null`，导致前端无法正确渲染视频。

## 可能的原因

### 1. Azure Speech API 配置问题 ✅ 已检查
- **状态**: 配置已存在
  - `AZURE_SPEECH_KEY`: 已配置
  - `AZURE_SPEECH_REGION`: `eastasia`
- **验证**: 环境变量已正确加载

### 2. 依赖包问题 ✅ 已检查
- **状态**: 依赖已安装
  - `azure-cognitiveservices-speech>=1.40.0`: 已安装

### 3. 可能的失败原因（需要进一步检查）

#### A. API 密钥无效或过期
- **症状**: Azure API 返回认证错误
- **检查方法**: 
  ```bash
  docker exec deepeye-backend-api-1 python -c "
  import azure.cognitiveservices.speech as speechsdk
  from app.core.config import settings
  speech_config = speechsdk.SpeechConfig(
      subscription=settings.AZURE_SPEECH_KEY,
      region=settings.AZURE_SPEECH_REGION
  )
  print('✅ Speech config created successfully')
  "
  ```

#### B. 网络连接问题
- **症状**: 请求超时或连接失败
- **检查方法**: 查看日志中的 "timeout" 或 "USP error"
- **解决方案**: 
  - 检查容器网络连接
  - 检查防火墙设置
  - 尝试增加重试次数和延迟

#### C. 音频生成部分失败
- **症状**: `generate_batch` 返回空列表
- **可能原因**:
  1. 所有音频片段生成都失败
  2. 异常被捕获但未记录
  3. 并行处理时出现竞态条件

#### D. 时间对齐失败
- **症状**: 音频生成成功，但 `time_range` 未添加
- **可能原因**:
  1. `TimeAligner.align_config` 抛出异常
  2. 音频片段 ID 不匹配
  3. 配置结构不符合预期

## 诊断步骤

### 1. 检查最新日志
```bash
# 查看视频生成相关的日志
docker logs deepeye-backend-api-1 2>&1 | grep -i "audio\|tts\|speech\|time_range\|align" | tail -50

# 查看错误日志
docker logs deepeye-backend-api-1 2>&1 | grep -i "error\|warning\|failed" | tail -50
```

### 2. 测试音频生成
```bash
docker exec deepeye-backend-api-1 python -c "
from app.node.video.config.audio_engine import TTSGenerator
from app.core.config import settings

try:
    generator = TTSGenerator(
        output_dir='/tmp/test_audio',
        api_key=settings.AZURE_SPEECH_KEY,
        region=settings.AZURE_SPEECH_REGION
    )
    result = generator.generate_audio(
        segment_id='test',
        text='这是一个测试',
        language='zh-CN',
        verbose=True
    )
    print(f'✅ 音频生成成功: {result.audio_file}')
except Exception as e:
    print(f'❌ 音频生成失败: {e}')
    import traceback
    traceback.print_exc()
"
```

### 3. 检查配置文件
```bash
# 查看最新生成的配置文件
docker exec deepeye-backend-api-1 cat /workspace/video_configs/generated_*_aligned.json | jq '.scenes[0] | {id, time_range, narration: .narration | map({text, time_start, time_end})}'
```

## 当前修复方案

### 后端修复 ✅
1. **添加默认时间范围**: 即使音频生成失败，也会添加基本的 `time_range`
2. **增强错误日志**: 记录详细的错误堆栈信息
3. **启用详细输出**: `verbose=True` 以便调试

### 前端修复 ✅
1. **自动计算时间范围**: 如果 `time_range` 缺失，从 `narration` 计算
2. **回退方案**: 使用估算值作为最后手段

## 下一步行动

1. **重新生成视频**: 触发一次新的视频生成，查看详细日志
2. **检查日志输出**: 关注以下信息：
   - "🚀 Starting parallel audio generation"
   - "✅ Generated: ..." 或 "❌ ... (error: ...)"
   - "Failed to generate audio: ..."
3. **验证修复**: 确认即使音频生成失败，配置文件也包含 `time_range`

## 长期解决方案

1. **添加健康检查**: 定期测试 Azure Speech API 连接
2. **改进错误处理**: 区分不同类型的失败（认证、网络、API限制等）
3. **添加重试机制**: 对于临时性错误（如网络超时）自动重试
4. **监控和告警**: 记录音频生成成功率，设置告警阈值
