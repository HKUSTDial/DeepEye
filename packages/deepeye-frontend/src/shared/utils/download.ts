export async function downloadFileFromUrl(url: string, filename: string) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('下载失败，请稍后再试')
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)

  try {
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
  } finally {
    URL.revokeObjectURL(objectUrl)
  }
}

