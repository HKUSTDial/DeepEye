declare module '@babel/standalone' {
  export function transform(
    source: string,
    options: { filename?: string; presets?: string[]; [key: string]: unknown }
  ): { code: string | null }
  export default { transform }
}
