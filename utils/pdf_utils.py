import fitz  # PyMuPDF库的别名
from llm_chat import chat

def int_to_rgb(color_int):
    red = (color_int >> 16) & 255
    green = (color_int >> 8) & 255
    blue = color_int & 255
    return (red / 255.0, green / 255.0, blue / 255.0)

def pdf_translate(input_path, output_path):
    # 打开原始PDF文件
    input_path = input_path
    doc = fitz.open(input_path)

    # 创建一个新的PDF文件对象
    output_doc = fitz.Document()
    # 中文字体(input_path)
    # 遍历原始PDF中的每一页
    for page in doc:
        print(f"************************************ Processing page {page.number + 1} ************************************")
        if page.number == 4:
            break
        # 复制原始页面到新PDF，并在新页面上进行处理
        new_page = output_doc.new_page()

        # 获取页面上的所有文字
        text_instances = page.get_text("dict")["blocks"]


        # 遍历每一段文字
        for block in text_instances:
            # 如果是图片则插入图片
            if block["type"] == 1:
                # 获取图片的bbox
                bbox = block["bbox"]
                # 获取页面的图片
                img = page.get_pixmap(matrix=fitz.Matrix(1, 1), clip=bbox)
                # 将图片插入到新页面中
                new_page.insert_image(bbox, pixmap=img)
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    # 获取原有文字和其位置
                    original_text = span["text"]
                    # 原始文字的底边位置（可能需要根据实际情况调整偏移量）
                    bottom_offset = span["bbox"][3]  # 假设向下偏移5个单位
                    left_offset = span["bbox"][0]  # 在原位置的左侧开始

                    # 获取原始文本颜色
                    original_color = int_to_rgb(span['color'])

                    # 计算新文本的矩形区域，这里简化处理，实际情况可能需要更精细的布局计算
                    new_rect = fitz.Rect(left_offset, bottom_offset,
                                         left_offset + 100, bottom_offset + 20)  # 宽度和高度仅为示例

                    # 组合新旧文本
                    if len(original_text) < 6:
                        translate_text = original_text
                    else:
                        system_prompt = "你是一个几十年资深的英中双鱼翻译官。请将我给的文字翻译成中文，翻译结果要达到专八水平，只输出翻译后的结果。如果无法翻译,或输入的是一串乱码或无意义的字符则直接输出数字0！注意：如果你无法翻译就直接输出数字0"
                        translate_text = chat(original_text, system_prompt)

                    if translate_text == '0':
                        translate_text = original_text
                    print(translate_text)

                    # 在计算的新位置插入组合文本
                    new_page.insert_text(new_rect.tl, translate_text, fontsize=span["size"], color=original_color, fontname='china-ss')

    # 保存修改后的PDF文件
    output_path = output_path
    output_doc.save(output_path)

    # 关闭PDF文件
    doc.close()
    output_doc.close()

if __name__ == '__main__':
    input_path = 'input.pdf'
    output_path = 'output_bak.pdf'
    pdf_translate(input_path, output_path)

