'use client'

interface SimpleMarkdownProps {
  content: string
  className?: string
}

export function SimpleMarkdown({ content, className = '' }: SimpleMarkdownProps) {
  // Simple markdown-like formatting without external dependencies
  const formatText = (text: string) => {
    let formatted = text

    // Code blocks with language
    formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre class="bg-muted rounded p-2 overflow-x-auto my-2"><code class="text-sm">${escapeHtml(code.trim())}</code></pre>`
    })

    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>')

    // Headers
    formatted = formatted.replace(/^### (.*$)/gim, '<h3 class="text-base font-bold mb-1 mt-2 first:mt-0">$1</h3>')
    formatted = formatted.replace(/^## (.*$)/gim, '<h2 class="text-lg font-bold mb-2 mt-3 first:mt-0">$1</h2>')
    formatted = formatted.replace(/^# (.*$)/gim, '<h1 class="text-xl font-bold mb-2 mt-4 first:mt-0">$1</h1>')

    // Bold
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold">$1</strong>')
    formatted = formatted.replace(/__(.*?)__/g, '<strong class="font-bold">$1</strong>')

    // Italic
    formatted = formatted.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>')
    formatted = formatted.replace(/_(.*?)_/g, '<em class="italic">$1</em>')

    // Links
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary hover:underline" target="_blank" rel="noopener noreferrer">$1</a>')

    // Blockquotes
    formatted = formatted.replace(/^> (.*$)/gim, '<blockquote class="border-l-4 border-primary pl-4 italic my-2">$1</blockquote>')

    // Lists - simple approach: wrap items
    formatted = formatted.replace(/^[\*\-] (.*$)/gim, '<li class="ml-4">$1</li>')
    formatted = formatted.replace(/^(\d+)\. (.*$)/gim, '<li class="ml-4">$2</li>')
    
    // Wrap consecutive list items
    formatted = formatted.replace(/(<li class="ml-4">.*<\/li>(\n|$))+/g, (match) => {
      return `<ul class="list-disc list-inside mb-2 space-y-1">${match}</ul>`
    })

    // Paragraphs: split by double newlines
    const paragraphs = formatted.split(/\n\n+/)
    formatted = paragraphs.map(para => {
      const trimmed = para.trim()
      if (!trimmed) return ''
      // If already has HTML tags, don't wrap
      if (trimmed.startsWith('<')) {
        return trimmed
      }
      // Convert single newlines to <br>
      const withBreaks = trimmed.replace(/\n/g, '<br>')
      return `<p class="mb-2 last:mb-0">${withBreaks}</p>`
    }).filter(p => p).join('')

    return formatted
  }

  const escapeHtml = (text: string) => {
    if (typeof window === 'undefined') {
      // Server-side: simple escape
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
    }
    // Client-side: use DOM
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  return (
    <div 
      className={`text-sm break-words ${className}`}
      dangerouslySetInnerHTML={{ __html: formatText(content) }}
    />
  )
}
