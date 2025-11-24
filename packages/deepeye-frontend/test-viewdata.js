// 测试脚本：验证 viewData 配置是否正确注册
// 在浏览器控制台运行此脚本

console.log('=== 测试 ViewData 配置 ===\n')

// 获取 registry
const registry = window.__REGISTRY__ || (() => {
  console.error('❌ Registry 未找到')
  return null
})()

if (registry) {
  // 测试几个关键节点
  const testNodes = ['ai.datacoder', 'ai.nl2sql', 'ai.dataplot']
  
  testNodes.forEach(nodeType => {
    const def = registry.get(nodeType)
    if (def) {
      console.log(`\n📦 ${nodeType}:`)
      console.log('  - viewData:', def.viewData)
      console.log('  - aiConfig:', def.aiConfig)
      console.log('  - inputs:', Object.keys(def.inputs))
      console.log('  - outputs:', Object.keys(def.outputs))
      console.log('  - properties:', Object.keys(def.properties))
    } else {
      console.log(`\n❌ ${nodeType}: 未找到`)
    }
  })
}

console.log('\n=== 测试完成 ===')

