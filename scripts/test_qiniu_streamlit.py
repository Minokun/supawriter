import os
import sys

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.qiniu_utils import ensure_public_image_url, is_protected_cdn_url

st.set_page_config(page_title="Qiniu Upload Test", page_icon="🖼️", layout="centered")

st.title("🖼️ Qiniu Upload Test")
st.caption("This page tests uploading an image URL to Qiniu using st.secrets.")

# Default Baidu CDN URL provided by the user
DEFAULT_URL = "https://bkimg.cdn.bcebos.com/pic/f7246b600c338744ebf832c55856cef9d72a60590a4b?x-bce-process=image/format,f_auto/resize,m_lfit,limit_1,h_1000"

with st.form("qiniu_test_form"):
    url = st.text_input("Image URL", value=DEFAULT_URL)
    force = st.checkbox("Force rehost (upload regardless of host)", value=False)
    submitted = st.form_submit_button("Run Test")

if submitted:
    if not url.strip():
        st.error("请输入有效的图片 URL")
    else:
        st.info(f"输入 URL: {url}")
        st.write(f"受保护CDN检测: {is_protected_cdn_url(url)}")

        try:
            if force:
                # Force upload: call lower-level upload to guarantee rehosting
                from utils.qiniu_utils import upload_image_from_url
                st.write("正在强制上传到七牛云...")
                new_url = upload_image_from_url(url)
            else:
                st.write("确保可公开访问（仅在检测到受保护CDN时上传）...")
                new_url = ensure_public_image_url(url)

            if new_url and new_url != url:
                st.success("上传成功，已替换为七牛云链接：")
                st.code(new_url, language="text")
                st.image(new_url, caption="Qiniu Hosted Image", use_container_width=True)
            elif new_url == url:
                st.warning("未进行上传（可能未检测为受保护CDN或上传被跳过），返回原始链接：")
                st.code(new_url or "", language="text")
                if new_url:
                    st.image(new_url, caption="Original Image (may fail to load)", use_container_width=True)
            else:
                st.error("上传失败，未返回链接。请检查st.secrets配置与网络连通性。")
        except Exception as e:
            st.exception(e)

st.divider()

# Show a quick view of required secrets presence (not values)
with st.expander("调试信息（仅显示配置是否存在）"):
    keys = ["QINIU_Domain", "QINIU_Folder", "QINIU_Accesskey", "QINIU_SecretKey"]
    for k in keys:
        st.write(f"{k}: ", "✅ 已配置" if (k in st.secrets) else "❌ 未配置")
