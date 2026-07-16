import streamlit as st
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import pandas as pd

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
tab1, tab2 = st.tabs(["📁 Upload Image File", "🔗 Process URLs & Excel"])

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
# TAB 2: URL & EXCEL BATCH PROCESSING
# ==========================================
with tab2:
    st.header("Process via URLs or Excel")
    
    # Feature A: Direct Single URL
    st.subheader("Direct Image URL")
    image_url = st.text_input("Paste a direct image URL here:")
    url_name = st.text_input("Name for this image (optional):", "direct_url_image")
    
    if st.button("Process URL") and image_url:
        with st.spinner("Fetching and processing URL..."):
            try:
                # Cloudinary can upload directly from a public URL
                upload_result = cloudinary.uploader.upload(image_url, public_id=url_name)
                transformed_url, options = cloudinary_url(
                    upload_result['public_id'],
                    width=660,
                    height=900,
                    crop="pad",
                    background="white",
                    format="jpg"
                )
                st.success("Success!")
                st.image(transformed_url, caption=f"Resized: {url_name}", width=300)
                st.markdown(f"[**Download {url_name}**]({transformed_url})", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Failed to process URL. Ensure it is a direct link to an image. Error: {e}")

    st.divider()

    # Feature B: Excel Bulk Upload
    st.subheader("Bulk Process via Excel")
    st.info("Format: Column A = Desired Name | Column B = Image 1 URL | Column C = Image 2 URL (etc.)")
    
    uploaded_excel = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])
    
    if uploaded_excel is not None:
        # Read the excel file using pandas
        df = pd.read_excel(uploaded_excel, header=None) # header=None so we just read raw columns
        st.write("Preview of your data:")
        st.dataframe(df.head())
        
        if st.button("Process Excel File"):
            st.write("### Results")
            
            # Loop through each row in the Excel sheet
            for index, row in df.iterrows():
                # Get the base name from Column A (index 0)
                base_name = str(row[0]).strip()
                
                # Get all remaining columns (the URLs) and drop empty cells
                urls = row[1:].dropna().tolist()
                
                if not urls:
                    continue
                
                st.markdown(f"**Processing Row: {base_name}**")
                
                # Loop through each URL in that row
                for i, url in enumerate(urls):
                    # Create a unique name: e.g., "ProductA_img1"
                    image_name = f"{base_name}_img{i+1}" 
                    
                    try:
                        upload_result = cloudinary.uploader.upload(str(url).strip(), public_id=image_name)
                        transformed_url, options = cloudinary_url(
                            upload_result['public_id'],
                            width=660,
                            height=900,
                            crop="pad",
                            background="white",
                            format="jpg"
                        )
                        st.markdown(f"- ✅ [{image_name} (Click to View/Download)]({transformed_url})")
                    except Exception as e:
                        st.error(f"- ❌ Failed {image_name}: URL might be broken or inaccessible.")
