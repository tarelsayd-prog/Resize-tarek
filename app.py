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
tab1, tab2, tab3 = st.tabs(["📁 Bulk File Upload (to Excel)", "🔗 Excel (Update Links)", "📦 Bulk Download (ZIP)"])

# ==========================================
# TAB 1: BULK FILE UPLOAD TO EXCEL (NEW)
# ==========================================
with tab1:
    st.header("Bulk Image Upload")
    st.write("Upload multiple images straight from your computer. The app will process them and give you an Excel sheet with all the new links.")
    
    # Notice the accept_multiple_files=True
    uploaded_files = st.file_uploader("Choose images...", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)

    if uploaded_files:
        st.info(f"Ready to process **{len(uploaded_files)}** images.")
        
        if st.button("Process Uploaded Images"):
            with st.spinner("Uploading and processing..."):
                results = []
                progress_bar = st.progress(0)
                
                for i, file in enumerate(uploaded_files):
                    try:
                        # Extract original filename without extension for the public_id
                        safe_name = file.name.rsplit('.', 1)[0]
                        
                        # Upload file directly to Cloudinary
                        upload_result = cloudinary.uploader.upload(file, public_id=safe_name)
                        
                        # Generate transformed URL
                        transformed_url, options = cloudinary_url(
                            upload_result['public_id'],
                            width=660, height=900, crop="pad", background="white", format="jpg"
                        )
                        
                        # Store success result
                        results.append({
                            "Original Filename": file.name,
                            "Cloudinary Link": transformed_url
                        })
                        
                    except Exception as e:
                        # Store error result
                        results.append({
                            "Original Filename": file.name,
                            "Cloudinary Link": f"ERROR: {str(e)}"
                        })
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                st.success("✅ All files processed!")
                
                # Display a preview table
                df_results = pd.DataFrame(results)
                st.dataframe(df_results, use_container_width=True)
                
                # Generate Excel file for download
                output_buffer = io.BytesIO()
                with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Download Excel with Links",
                    data=output_buffer.getvalue(),
                    file_name="uploaded_image_links.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

# ==========================================
# TAB 2: EXCEL BATCH PROCESSING (URLS)
# ==========================================
with tab2:
    st.header("Excel Link Updater")
    st.info("Format: Column A = Desired Name | Column B = Image 1 URL | Column C = Image 2 URL (etc.)")
    uploaded_excel = st.file_uploader("Upload Excel file", type=["xlsx", "xls"], key="tab2_upload")
    
    if uploaded_excel is not None:
        df = pd.read_excel(uploaded_excel, header=None)
        if st.button("Process Links"):
            st.write("Processing... (2-second pause between images to prevent blocks)")
            output_df = df.copy()
            progress_bar_tab2 = st.progress(0)
            
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
                progress_bar_tab2.progress((row_idx + 1) / len(df))
            
            st.success("✅ Complete!")
            output_buffer2 = io.BytesIO()
            with pd.ExcelWriter(output_buffer2, engine='openpyxl') as writer:
                output_df.to_excel(writer, index=False, header=False)
            st.download_button("📥 Download Updated Excel", data=output_buffer2.getvalue(), file_name="processed_links.xlsx", type="primary")

# ==========================================
# TAB 3: BULK DOWNLOAD TO ZIP 
# ==========================================
with tab3:
    st.header("Bulk Image Downloader")
    st.write("Upload an Excel file or paste links directly. The app will process them and generate a single ZIP file containing all the final images.")
    
    input_method = st.radio("Choose Input Method:", ["Upload Excel file", "Paste Bulk Links"])
    
    links_to_process = []
    
    if input_method == "Paste Bulk Links":
        pasted_links = st.text_area("Paste image links here (one link per line):", height=200)
        if pasted_links:
            for idx, line in enumerate(pasted_links.split('\n')):
                clean_link = line.strip()
                if clean_link:
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
    
    if len(links_to_process) > 0:
        st.write(f"Total images found: **{len(links_to_process)}**")
        
        if st.button("Process and Generate ZIP"):
            zip_buffer = io.BytesIO()
            progress_bar_zip = st.progress(0)
            status_text = st.empty()
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for i, item in enumerate(links_to_process):
                    status_text.text(f"Processing: {item['name']}...")
                    try:
                        direct_url = convert_gdrive_url(item["url"])
                        upload_result = cloudinary.uploader.upload(direct_url, public_id=item["name"])
                        transformed_url, options = cloudinary_url(
                            upload_result['public_id'],
                            width=660, height=900, crop="pad", background="white", format="jpg"
                        )
                        
                        img_response = requests.get(transformed_url)
                        if img_response.status_code == 200:
                            zip_file.writestr(f"{item['name']}.jpg", img_response.content)
                        else:
                            st.error(f"Could not fetch image data for {item['name']}.")
                            
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
