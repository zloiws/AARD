'use client'

import { useMemo } from 'react'
import { SimpleMarkdown } from './simple-markdown'

interface ReasoningHighlightProps {
  content: string
}

export function ReasoningHighlight({ content }: ReasoningHighlightProps) {
  // Highlight important parts in reasoning
  const highlightedContent = useMemo(() => {
    let text = content
    
    // Highlight decision points (keywords like "decide", "choose", "conclude", "therefore", "thus")
    const decisionPatterns = [
      /\b(decide|decided|decision)\b/gi,
      /\b(choose|chosen|choice)\b/gi,
      /\b(conclude|conclusion|concluded)\b/gi,
      /\b(therefore|thus|hence|so)\b/gi,
      /\b(because|since|as)\b/gi,
      /\b(important|critical|crucial|key)\b/gi,
      /\b(should|must|need to|required)\b/gi,
    ]
    
    decisionPatterns.forEach(pattern => {
      text = text.replace(pattern, (match) => {
        return `**${match}**`
      })
    })
    
    // Highlight numbers and percentages (often important metrics)
    text = text.replace(/\b(\d+%?)\b/g, '**$1**')
    
    // Highlight "if-then" logic
    text = text.replace(/\b(if\s+[^,]+,\s*then)\b/gi, '**$1**')
    
    return text
  }, [content])

  return <SimpleMarkdown content={highlightedContent} />
}
