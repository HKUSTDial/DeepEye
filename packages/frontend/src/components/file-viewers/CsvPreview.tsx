type CsvPreviewProps = {
  headers: string[]
  rows: string[][]
}

export default function CsvPreview({ headers, rows }: CsvPreviewProps) {
  return (
    <div className="csv-viewer">
      <table className="csv-table">
        <thead>
          <tr>
            <th className="csv-row-number">#</th>
            {headers.map((header, index) => (
              <th key={index}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              <td className="csv-row-number">{rowIndex + 1}</td>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
