declare module '*.md' {
  let md: string
  export default md
}

declare module '*.svg' {
  const content: React.FC<React.SVGProps<SVGSVGElement>>
  export default content
}
