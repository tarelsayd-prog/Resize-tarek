import streamlit as st
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import pandas as pd
import io
import re
import time
import zipfile
import requests

# Page configuration
st.set_page_config(page_title="Image Resizer Pro", layout="wide")

# Securely configure Cloudinary using Streamlit Secrets
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except KeyError:
    st.error("Missing Cloudinary keys! Please add them to your Streamlit Cloud settings under 'Secrets'.")
    st.stop()

# Helper function to convert Google Drive viewer links to direct download links
def convert_gdrive_url(url):
    url_str = str(url).strip()
    if "drive.google.com/file/d/" in url_str:
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url_str)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url_str

st.title("Image Resizer Pro (660x900)")
st.write("Resize images to exactly 660x900 (0.73 aspect ratio) with a white background.")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📁 Single File", "🔗 Excel (Update Links)", "📦 Bulk Download (ZIP)"])

# ==========================================
# TAB 1: ORIGINAL FILE UPLOAD
# ==========================================
with tab1:
    st.header("Single Image Upload")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Original Image", width=300)
        
        if st.button("Process Single Image"):
            with st.spinner("Uploading and processing..."):
                try:
                    upload_result = cloudinary.uploader.upload(uploaded_file)
                    transformed_url, options = cloudinary_url(
                        upload_result['public_id'],
                        width=660, height=900, crop="pad", background="white", format="jpg"
                    )
                    st.success("Success!")
                    st.image(transformed_url, caption="Resized Image", width=300)
                    st.markdown(f"[**Download Resized Image**]({transformed_url})", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# ==========================================
# TAB 2: EXCEL BATCH PROCESSING (URLS)
# ==========================================
with tab2:
    st.header("Excel Link Updater")
    st.info("Returns an Excel sheet with new Cloudinary links.")
    uploaded_excel = st.file_uploader("Upload Excel file", type=["xlsx", "xls"], key="tab2_upload")
    
    if uploaded_excel is not None:
        df = pd.read_excel(uploaded_excel, header=None)
        if st.button("Process Links"):
            st.write("Processing... (2-second pause between images to prevent blocks)")
            output_df = df.copy()
            progress_bar = st.progress(0)
            
            for row_idx, row in df.iterrows():
                base_name = str(row[0]).strip()
                for col_idx in range(1, len(row)):
                    original_url = row[col_idx]
                    if pd.notna(original_url) and str(original_url).strip() != "":
                        try:
                            direct_url = convert_gdrive_url(original_url)
                            upload_result = cloudinary.uploader.upload(direct_url, public_id=f"{base_name}_img{col_idx}")
                            transformed_url, _ = cloudinary_url(
                                upload_result['public_id'], width=660, height=900, crop="pad", background="white", format="jpg"
                            )
                            output_df.iat[row_idx, col_idx] = transformed_url
                            time.sleep(2)
                        except Exception as e:
                            output_df.iat[row_idx, col_idx] = f"ERROR: {str(e)}"
                progress_bar.progress((row_idx + 1) / len(df))
            
            st.success("✅ Complete!")
            output_buffer = io.BytesIO()
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                output_df.to_excel(writer, index=False, header=False)
            st.download_button("📥 Download Updated Excel", data=output_buffer.getvalue(), file_name="processed_links.xlsx")

# ==========================================
# TAB 3: BULK DOWNLOAD TO ZIP (NEW)
# ==========================================
with tab3:
    st.header("Bulk Image Downloader")
    st.write("Upload an Excel file or paste links directly. The app will process them and generate a single ZIP file containing all the final images.")
    
    input_method = st.radio("Choose Input Method:", ["Upload Excel file", "Paste Bulk Links"])
    
    links_to_process = [] # Will store a list of dictionaries: {"name": "filename", "url": "http..."}
    
    if input_method == "Paste Bulk Links":
        pasted_links = st.text_area("Paste image links here (one link per line):", height=200)
        if pasted_links:
            # Split the text area into individual lines
            for idx, line in enumerate(pasted_links.split('\n')):
                clean_link = line.strip()
                if clean_link:
                    # Automatically generate a generic name for pasted links
                    links_to_process.append({"name": f"image_{idx+1}", "url": clean_link})
                    
    elif input_method == "Upload Excel file":
        st.info("Format: Column A = Desired File Name | Column B = Image 1 URL | Column C = Image 2 URL (etc.)")
        uploaded_excel_zip = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"], key="tab3_upload")
        
        if uploaded_excel_zip is not None:
            df_zip = pd.read_excel(uploaded_excel_zip, header=None)
            for row_idx, row in df_zip.iterrows():
                base_name = str(row[0]).strip()
                for col_idx in range(1, len(row)):
                    url = row[col_idx]
                    if pd.notna(url) and str(url).strip() != "":
                         image_name = f"{base_name}_img{col_idx}"
                         links_to_process.append({"name": image_name, "url": str(url).strip()})
    
    # Processing block for ZIP creation
    if len(links_to_process) > 0:
        st.write(f"Total images found: **{len(links_to_process)}**")
        
        if st.button("Process and Generate ZIP"):
            zip_buffer = io.BytesIO()
            progress_bar_zip = st.progress(0)
            status_text = st.empty()
            
            # Create the ZIP file in memory
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for i, item in enumerate(links_to_process):
                    status_text.text(f"Processing: {item['name']}...")
                    try:
                        # 1. Convert Drive URL if needed
                        direct_url = convert_gdrive_url(item["url"])
                        
                        # 2. Upload to Cloudinary
                        upload_result = cloudinary.uploader.upload(direct_url, public_id=item["name"])
                        
                        # 3. Generate Cloudinary link
                        transformed_url, options = cloudinary_url(
                            upload_result['public_id'],
                            width=660, height=900, crop="pad", background="white", format="jpg"
                        )
                        
                        # 4. Download the actual image file from Cloudinary
                        img_response = requests.get(transformed_url)
                        if img_response.status_code == 200:
                            # 5. Write the image file into the ZIP archive
                            zip_file.writestr(f"{item['name']}.jpg", img_response.content)
                        else:
                            st.error(f"Could not fetch image data for {item['name']}.")
                            
                        # 2-second pause to protect against rate limits
                        time.sleep(2)
                        
                    except Exception as e:
                        st.error(f"Error processing {item['name']}: {e}")
                        
                    progress_bar_zip.progress((i + 1) / len(links_to_process))
            
            status_text.text("✅ All images processed and zipped successfully!")
            
            st.download_button(
                label="📦 Download Images (ZIP Archive)",
                data=zip_buffer.getvalue(),
                file_name="processed_images.zip",
                mime="application/zip",
                type="primary"
            )
