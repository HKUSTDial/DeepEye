/**
 * 在浏览器中编译 TSX 源码并返回导出的 React 组件。
 * 用于从后端拉取新生成的场景 TSX 后动态运行，使「下次请求」生成的视频能直接预览。
 * 使用动态 import 加载 @babel/standalone，避免构建时解析失败（如 Docker 环境未安装该依赖）。
 */

import React from 'react'
import * as Remotion from 'remotion'
import * as d3 from 'd3'

type BabelStandalone = { transform: (source: string, options: object) => { code: string | null } }
type DynamicSceneProps = Record<string, unknown>
type SceneComponent = React.FC<DynamicSceneProps>

let babelPromise: Promise<BabelStandalone> | null = null

/** 懒加载 @babel/standalone，仅在首次编译时请求 */
export function loadBabel(): Promise<BabelStandalone> {
  if (!babelPromise) {
    // Vite 会预构建 @babel/standalone，所以动态 import 可以正常工作
    babelPromise = import('@babel/standalone').then((m) => (m.default ?? m) as BabelStandalone)
  }
  return babelPromise
}

const REMOTION_NAMESPACE = '__INJECT_REMOTION__'
const REACT_NAMESPACE = '__INJECT_REACT__'
const D3_NAMESPACE = '__INJECT_D3__'

/** 把 TSX 里的 react/remotion 的 import 替换成注入变量，便于编译后直接执行 */
function injectImports(source: string): string {
  return source
    // 处理 import React from 'react' 或 import React, { ... } from 'react'
    .replace(/import\s+React(?:\s*,\s*\{([^}]+)\})?\s+from\s+['"]react['"]\s*;?\s*\n?/g, (_, namedImports) => {
      if (namedImports) {
        const list = namedImports.split(',').map((s: string) => s.trim()).filter(Boolean)
        return `const React = ${REACT_NAMESPACE};\nconst { ${list.join(', ')} } = React;\n`
      }
      return `const React = ${REACT_NAMESPACE};\n`
    })
    // 处理 import { ... } from 'react'
    .replace(/import\s+\{([^}]+)\}\s+from\s+['"]react['"]\s*;?\s*\n?/g, (_, names) => {
      const list = names.split(',').map((s: string) => s.trim()).filter(Boolean)
      return `const { ${list.join(', ')} } = ${REACT_NAMESPACE};\n`
    })
    // 处理 import * as X from 'react'
    .replace(/import\s+\*\s+as\s+(\w+)\s+from\s+['"]react['"]\s*;?\s*\n?/g, `const $1 = ${REACT_NAMESPACE};\n`)
    // 处理 import { ... } from 'remotion'
    .replace(/import\s+\{([^}]+)\}\s+from\s+['"]remotion['"]\s*;?\s*\n?/g, (_, names) => {
      const list = names.split(',').map((s: string) => s.trim()).filter(Boolean)
      return `const { ${list.join(', ')} } = ${REMOTION_NAMESPACE};\n`
    })
    // 处理 import * as X from 'remotion'
    .replace(/import\s+\*\s+as\s+(\w+)\s+from\s+['"]remotion['"]\s*;?\s*\n?/g, `const $1 = ${REMOTION_NAMESPACE};\n`)
    // 处理 import * as d3 from 'd3'
    .replace(/import\s+\*\s+as\s+d3\s+from\s+['"]d3['"]\s*;?\s*\n?/g, `const d3 = ${D3_NAMESPACE};\n`)
    // 处理其他 import，移除它们（因为浏览器中无法解析）
    .replace(/import\s+.*?from\s+['"][^'"]+['"]\s*;?\s*\n?/g, '')
}

/** 移除 declare module '...' { ... } 块（支持嵌套 {}），避免在 sourceType: 'script' 下 Babel 报错 */
function stripDeclareModuleBlocks(source: string): string {
  const declModuleRegex = /declare\s+module\s+['"][^'"]+['"]\s*\{/g
  let out = source
  let match: RegExpExecArray | null
  while ((match = declModuleRegex.exec(source)) !== null) {
    const braceStart = match.index + match[0].length
    let depth = 1
    let i = braceStart
    while (i < source.length && depth > 0) {
      const c = source[i]
      if (c === '{') depth++
      else if (c === '}') depth--
      i++
    }
    const end = depth === 0 ? i : source.length
    const block = source.slice(match.index, end)
    out = out.replace(block, '/* declare module block removed for browser compile */\n')
  }
  return out
}

/** 修复后端生成 TSX 时可能被截断的 .style('filter', 'drop-shadow(...rgba(NNN' 未闭合字符串（整行替换为合法值） */
function repairUnterminatedFilterStrings(source: string): string {
  return source.replace(
    /\.style\s*\(\s*['"]filter['"]\s*,\s*['"]drop-shadow\s*\(\s*0\s+0\s+15px\s+rgba\s*\(\s*(\d+)[^\n]*$/gm,
    ".style('filter', 'drop-shadow(0 0 15px rgba($1, 107, 107, 0.8))');",
  )
}

/** 把 export const X = ... 或 export const X: Type = ... 转为 const X = ... 并收集导出名 */
function wrapExports(source: string): string {
  const exportNames: string[] = []
  let out = source
    // 处理 export const X = ... 或 export const X: Type = ...（包括中文字符的变量名）
    .replace(/export\s+const\s+([\w\u4e00-\u9fa5]+)\s*(?::\s*[^=]+)?\s*=/g, (_, name) => {
      exportNames.push(name)
      return `const ${name} = `
    })
    // 处理 export default ...
    .replace(/export\s+default\s+/g, 'const __default_export__ = ')
    // 移除其他 export 语句（如 export { ... }）
    .replace(/export\s+\{[^}]+\}\s*;?\s*\n?/g, '')
  
  if (exportNames.length > 0 || out.includes('__default_export__')) {
    const assign = exportNames.length
      ? `__EXPORTS__.named = { ${exportNames.join(', ')} };`
      : ''
    const defaultAssign = out.includes('__default_export__')
      ? 'if (typeof __default_export__ !== "undefined") __EXPORTS__.default = __default_export__;'
      : ''
    out += `\n${assign}\n${defaultAssign}\n`
  }
  return out
}

export async function compileTsxAndGetComponent(
  tsxSource: string,
  filename: string = 'Scene.tsx'
): Promise<SceneComponent | null> {
  try {
    const Babel = await loadBabel()
    let source = stripDeclareModuleBlocks(tsxSource)
    source = repairUnterminatedFilterStrings(source)
    source = injectImports(source)
    source = wrapExports(source)
    const result = Babel.transform(source, {
      filename,
      presets: [
        ['react', { runtime: 'classic' }],
        ['typescript', { isTSX: true, allExtensions: true }],
      ],
      sourceType: 'script',
    })
    const code = result.code
    if (!code) return null

    const __EXPORTS__: { default?: SceneComponent; named?: Record<string, SceneComponent> } = {}
    const fn = new Function(REACT_NAMESPACE, REMOTION_NAMESPACE, D3_NAMESPACE, '__EXPORTS__', code)
    fn(React, Remotion, d3, __EXPORTS__)

    const comp = __EXPORTS__.default ?? (__EXPORTS__.named && Object.values(__EXPORTS__.named).find((v) => typeof v === 'function'))
    return (comp as SceneComponent) ?? null
  } catch (e) {
    console.warn('[compileTsxInBrowser]', filename, e)
    return null
  }
}

/** 同步版：需要先调用 loadBabel() 再使用，适用于已预加载 Babel 的场景 */
export function compileTsxAndGetComponentSync(
  tsxSource: string,
  filename: string,
  Babel: BabelStandalone
): SceneComponent | null {
  try {
    let source = stripDeclareModuleBlocks(tsxSource)
    source = repairUnterminatedFilterStrings(source)
    source = injectImports(source)
    source = wrapExports(source)
    const result = Babel.transform(source, {
      filename,
      presets: [
        ['react', { runtime: 'classic' }],
        ['typescript', { isTSX: true, allExtensions: true }],
      ],
      sourceType: 'script',
    })
    const code = result.code
    if (!code) return null
    const __EXPORTS__: { default?: SceneComponent; named?: Record<string, SceneComponent> } = {}
    const fn = new Function(REACT_NAMESPACE, REMOTION_NAMESPACE, D3_NAMESPACE, '__EXPORTS__', code)
    fn(React, Remotion, d3, __EXPORTS__)
    const comp = __EXPORTS__.default ?? (__EXPORTS__.named && Object.values(__EXPORTS__.named).find((v) => typeof v === 'function'))
    return (comp as SceneComponent) ?? null
  } catch (e) {
    console.warn('[compileTsxInBrowser]', filename, e)
    return null
  }
}
