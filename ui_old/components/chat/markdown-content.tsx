'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

interface MarkdownContentProps {
  content: string
  className?: string
}

export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  return (
    <div className={`prose prose-sm dark:prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '')
            return !inline && match ? (
              <pre className="bg-muted rounded p-2 overflow-x-auto [&>code]:bg-transparent [&>code]:p-0">
                <code className={className} {...props}>
                  {children}
                </code>
              </pre>
            ) : (
              <code className="bg-muted px-1 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            )
          },
          p({ children }: any) {
            return <p className="mb-2 last:mb-0">{children}</p>
          },
          ul({ children }: any) {
            return <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>
          },
          ol({ children }: any) {
            return <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>
          },
          li({ children }: any) {
            return <li className="ml-4">{children}</li>
          },
          h1({ children }: any) {
            return <h1 className="text-xl font-bold mb-2 mt-4 first:mt-0">{children}</h1>
          },
          h2({ children }: any) {
            return <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h2>
          },
          h3({ children }: any) {
            return <h3 className="text-base font-bold mb-1 mt-2 first:mt-0">{children}</h3>
          },
          blockquote({ children }: any) {
            return <blockquote className="border-l-4 border-primary pl-4 italic my-2">{children}</blockquote>
          },
          a({ href, children }: any) {
            return (
              <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            )
          },
          strong({ children }: any) {
            return <strong className="font-bold">{children}</strong>
          },
          em({ children }: any) {
            return <em className="italic">{children}</em>
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
