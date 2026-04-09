/**
 * WeChat Article Preview Styles
 * 仿公众号文章预览样式
 */

export interface WeChatStyles {
  container: string;
  h1: string;
  h2: string;
  h3: string;
  h4: string;
  p: string;
  ul: string;
  ol: string;
  li: string;
  blockquote: string;
  code: string;
  pre: string;
  img: string;
  a: string;
  strong: string;
  em: string;
  table: string;
  tableWrapper: string;
  th: string;
  td: string;
  hr: string;
}

export const weChatStyles: WeChatStyles = {
  container:
    'font-family -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.8; color: #333; padding: 20px; background-color: #fff;',
  h1: 'font-size: 22px; font-weight: bold; margin-top: 30px; margin-bottom: 15px; color: #333; text-align: center;',
  h2: 'font-size: 18px; font-weight: bold; margin-top: 30px; margin-bottom: 15px; padding-left: 10px; border-left: 4px solid #07c160; color: #333; line-height: 1.4;',
  h3: 'font-size: 16px; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #333; display: flex; align-items: center; padding-left: 8px; border-left: 3px solid #07c160;',
  h4: 'font-size: 15px; font-weight: bold; margin-top: 15px; margin-bottom: 8px; color: #333;',
  p: 'font-size: 16px; line-height: 1.8; margin-bottom: 20px; color: #333; text-align: justify;',
  ul: 'margin-bottom: 20px; padding-left: 20px; color: #333; list-style-type: disc;',
  ol: 'margin-bottom: 20px; padding-left: 20px; color: #333; list-style-type: decimal;',
  li: 'font-size: 16px; line-height: 1.8; margin-bottom: 8px;',
  blockquote:
    'padding: 15px; margin: 20px 0; border-left: 4px solid #07c160; background-color: #f7f7f7; color: #888; font-size: 15px; line-height: 1.6; border-radius: 4px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);',
  code: 'font-family: Menlo, Monaco, Consolas, "Courier New", monospace; font-size: 14px; background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; color: #d63384;',
  pre: 'background-color: #282c34; padding: 15px; overflow-x: auto; border-radius: 5px; margin-bottom: 20px; color: #abb2bf; font-family: Menlo, Monaco, Consolas, "Courier New", monospace; font-size: 13px; line-height: 1.5;',
  img: 'max-width: 100%; height: auto; display: block; margin: 20px auto; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s;',
  a: 'color: #07c160; text-decoration: none; border-bottom: 1px dashed #07c160;',
  strong: 'font-weight: bold; color: #333;',
  em: 'font-style: italic;',
  table: 'width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; border: 1px solid #e0e0e0;',
  tableWrapper: 'overflow-x: auto; margin-bottom: 20px; max-width: 100%;',
  th: 'background-color: #07c160; color: #ffffff; border: 1px solid #e0e0e0; padding: 10px; text-align: left; font-weight: bold;',
  td: 'border: 1px solid #e0e0e0; padding: 10px;',
  hr: 'border: 0; border-top: 1px solid #eee; margin: 30px 0;',
};

/**
 * Modern clean styles for article preview
 */
export const modernStyles: WeChatStyles = {
  container:
    'font-family -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 16px; line-height: 1.7; color: #1a1a1a; padding: 24px; background-color: #ffffff;',
  h1: 'font-size: 28px; font-weight: 700; margin-top: 32px; margin-bottom: 16px; color: #111827; letter-spacing: -0.025em;',
  h2: 'font-size: 22px; font-weight: 600; margin-top: 28px; margin-bottom: 14px; color: #1f2937; padding-bottom: 8px; border-bottom: 2px solid #e5e7eb;',
  h3: 'font-size: 18px; font-weight: 600; margin-top: 24px; margin-bottom: 12px; color: #374151;',
  h4: 'font-size: 16px; font-weight: 600; margin-top: 20px; margin-bottom: 10px; color: #4b5563;',
  p: 'font-size: 16px; line-height: 1.75; margin-bottom: 16px; color: #374151;',
  ul: 'margin-bottom: 16px; padding-left: 24px; color: #374151;',
  ol: 'margin-bottom: 16px; padding-left: 24px; color: #374151;',
  li: 'font-size: 16px; line-height: 1.75; margin-bottom: 6px;',
  blockquote:
    'padding: 16px 20px; margin: 20px 0; border-left: 4px solid #6366f1; background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); color: #64748b; font-size: 15px; border-radius: 0 8px 8px 0;',
  code: 'font-family: "JetBrains Mono", "Fira Code", Consolas, monospace; font-size: 14px; background-color: #f3f4f6; padding: 2px 6px; border-radius: 4px; color: #e11d48; font-weight: 500;',
  pre: 'background-color: #1e293b; padding: 16px; overflow-x: auto; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);',
  img: 'max-width: 100%; height: auto; display: block; margin: 24px auto; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); cursor: pointer; transition: all 0.2s;',
  a: 'color: #6366f1; text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.2s;',
  strong: 'font-weight: 600; color: #111827;',
  em: 'font-style: italic; color: #4b5563;',
  table: 'width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);',
  tableWrapper: 'overflow-x: auto; margin-bottom: 20px;',
  th: 'background-color: #f8fafc; color: #1e293b; border: 1px solid #e2e8f0; padding: 12px 16px; text-align: left; font-weight: 600;',
  td: 'border: 1px solid #e2e8f0; padding: 12px 16px;',
  hr: 'border: 0; border-top: 2px solid #e5e7eb; margin: 32px 0;',
};

/**
 * GitHub-like styles for developers
 */
export const githubStyles: WeChatStyles = {
  container:
    'font-family -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.5; color: #24292f; padding: 16px; background-color: #ffffff;',
  h1: 'font-size: 2em; font-weight: 600; margin-top: 24px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #d0d7de;',
  h2: 'font-size: 1.5em; font-weight: 600; margin-top: 24px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #d0d7de;',
  h3: 'font-size: 1.25em; font-weight: 600; margin-top: 24px; margin-bottom: 16px;',
  h4: 'font-size: 1em; font-weight: 600; margin-top: 16px; margin-bottom: 8px;',
  p: 'font-size: 16px; line-height: 1.5; margin-bottom: 16px;',
  ul: 'margin-bottom: 16px; padding-left: 32px;',
  ol: 'margin-bottom: 16px; padding-left: 32px;',
  li: 'margin-top: 4px;',
  blockquote:
    'padding: 0 1em; margin: 16px 0; color: #57606a; border-left: 4px solid #d0d7de;',
  code: 'font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace; font-size: 85%; background-color: rgba(175,184,193,0.2); padding: 2px 4px; border-radius: 6px;',
  pre: 'background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 6px; margin-bottom: 16px; font-size: 85%;',
  img: 'max-width: 100%; height: auto; display: block; margin: 16px auto; border-radius: 6px; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.12);',
  a: 'color: #0969da; text-decoration: none;',
  strong: 'font-weight: 600;',
  em: 'font-style: italic;',
  table: 'width: 100%; border-collapse: collapse; margin-bottom: 16px; display: block; overflow: auto;',
  tableWrapper: 'overflow-x: auto; margin-bottom: 16px;',
  th: 'background-color: #f6f8fa; border: 1px solid #d0d7de; padding: 6px 13px; font-weight: 600;',
  td: 'border: 1px solid #d0d7de; padding: 6px 13px;',
  hr: 'border: 0; border-top: 1px solid #d0d7de; margin: 24px 0;',
};

export type PreviewStyle = 'wechat' | 'modern' | 'github';

export const getStyles = (style: PreviewStyle = 'wechat'): WeChatStyles => {
  switch (style) {
    case 'modern':
      return modernStyles;
    case 'github':
      return githubStyles;
    default:
      return weChatStyles;
  }
};
