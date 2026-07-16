import streamlit as st
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Page configuration
st.set_page_config(page_title="Image Resizer", layout="centered")

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

st.title("Image Resizer")
st.write("Upload an image to resize it exactly to 660x900 (0.73 aspect ratio) with a white background.")

# File uploader
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is not None:
    # Show the original image
    st.image(uploaded_file, caption="Original Image", use_container_width=True)
    
    if st.button("Process Image"):
        with st.spinner("Uploading and processing via Cloudinary..."):
            try:
                # Upload the raw file to Cloudinary
                upload_result = cloudinary.uploader.upload(uploaded_file)
                
                # Generate the transformation URL
                # crop="pad" ensures the whole image fits without distortion
                # background="white" fills the empty space
                # format="jpg" ensures transparency turns into solid white
                transformed_url, options = cloudinary_url(
                    upload_result['public_id'],
                    width=660,
                    height=900,
                    crop="pad",
                    background="white",
                    format="jpg"
                )
                
                st.success("Image processed successfully!")
                
                # Display the final result
                st.image(transformed_url, caption="Resized Image (660x900)", use_container_width=True)
                
                # Provide a clickable download link
                st.markdown(f"[**Click here to download your resized image**]({transformed_url})", unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
