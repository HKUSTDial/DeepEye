type LineNumberTextPreviewProps = {
  lines: string[]
}

export default function LineNumberTextPreview({ lines }: LineNumberTextPreviewProps) {
  return (
    <div className="text-viewer">
      <table className="text-viewer-table">
        <tbody>
          {lines.map((line, index) => (
            <tr key={index} className="text-line">
              <td className="line-number">{index + 1}</td>
              <td className="line-content">
                <pre>{line}</pre>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
