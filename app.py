import streamlit as st
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import pandas as pd
import io

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

st.title("Image Resizer Pro (660x900)")
st.write("Resize images to exactly 660x900 (0.73 aspect ratio) with a white background.")

# Create two tabs for the different tools
tab1, tab2 = st.tabs(["📁 Single File Upload", "🔗 Excel Batch Processor"])

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
                        width=660,
                        height=900,
                        crop="pad",
                        background="white",
                        format="jpg"
                    )
                    st.success("Success!")
                    st.image(transformed_url, caption="Resized Image", width=300)
                    st.markdown(f"[**Download Resized Image**]({transformed_url})", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# ==========================================
# TAB 2: EXCEL BATCH PROCESSING
# ==========================================
with tab2:
    st.header("Bulk Process via Excel")
    st.info("Format: Column A = Desired Name | Column B = Image 1 URL | Column C = Image 2 URL (etc.)")
    
    uploaded_excel = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])
    
    if uploaded_excel is not None:
        # Read the excel file using pandas
        df = pd.read_excel(uploaded_excel, header=None)
        
        st.write("Preview of original data:")
        st.dataframe(df.head())
        
        if st.button("Start Batch Processing"):
            st.write("Processing images... Please wait.")
            
            output_df = df.copy()
            progress_bar = st.progress(0)
            total_rows = len(df)
            
            for row_idx, row in df.iterrows():
                base_name = str(row[0]).strip()
                
                for col_idx in range(1, len(row)):
                    original_url = row[col_idx]
                    
                    if pd.notna(original_url) and str(original_url).strip() != "":
                        image_name = f"{base_name}_img{col_idx}" 
                        
                        try:
                            # Upload to Cloudinary
                            upload_result = cloudinary.uploader.upload(str(original_url).strip(), public_id=image_name)
                            
                            # Generate the URL ending in .jpg
                            transformed_url, options = cloudinary_url(
                                upload_result['public_id'],
                                width=660,
                                height=900,
                                crop="pad",
                                background="white",
                                format="jpg"
                            )
                            
                            output_df.iat[row_idx, col_idx] = transformed_url
                            
                        except Exception as e:
                            # Capture the exact error message
                            error_msg = str(e)
                            st.warning(f"Failed to process '{base_name}' at column {col_idx+1}. Reason: {error_msg}")
                            output_df.iat[row_idx, col_idx] = f"ERROR: {error_msg}"
                
                progress_bar.progress((row_idx + 1) / total_rows)
            
            st.success("✅ Processing Complete!")
            
            st.write("Preview of new data:")
            st.dataframe(output_df.head())
            
            output_buffer = io.BytesIO()
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                output_df.to_excel(writer, index=False, header=False)
            
            st.download_button(
                label="📥 Download Updated Excel File",
                data=output_buffer.getvalue(),
                file_name="processed_images.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
