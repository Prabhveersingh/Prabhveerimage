import streamlit as st
import requests
import io
import zipfile
from datetime import datetime
from urllib.parse import quote

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="Text 2 Img by PS333",
    page_icon="🧠",
    layout="centered"
)

# ----------------------------
# Helpers
# ----------------------------
RATIO_PRESETS = {
    "1:1 (Square)": (1024, 1024),
    "9:16 (Reels/Shorts)": (768, 1365),
    "16:9 (Landscape)": (1365, 768),
    "4:5 (Instagram Post)": (1024, 1280),
}

def build_prompt(style: str, prompt: str, negative: str) -> str:
    # Negative prompt ko seedha append kar rahe (Pollinations pe kaafi cases me help karta)
    # If API ignores it, still prompt improves consistency.
    base = f"{style} style, {prompt}".strip()
    if negative.strip():
        base += f". Negative prompt: {negative.strip()}"
    return base

def pollinations_url(final_prompt: str, width: int, height: int, seed: int | None) -> str:
    # Pollinations prompt encode
    encoded = quote(final_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}"
    if seed is not None:
        url += f"&seed={seed}"
    return url

@st.cache_data(show_spinner=False, ttl=60 * 60)
def fetch_image_bytes(url: str) -> bytes:
    # Cached download for stability
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content

def to_zip(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files:
            z.writestr(name, data)
    buf.seek(0)
    return buf.read()

def init_state():
    if "history" not in st.session_state:
        st.session_state.history = []  # list of dicts: {url, prompt, style, w, h, seed, ts}
    if "favorites" not in st.session_state:
        st.session_state.favorites = []  # same format

init_state()

# ----------------------------
# Header
# ----------------------------
st.image(
    "https://i.ibb.co/hJVMdhNV/Photo-Fixer-Bot-aifaceswap-dac4ce0cdd00acf259c01808d4253130.jpg",
    width=250
)
st.title("🔥 PS333 Image Generator 🔥")
st.caption("Powered by Pollinations • Advanced UI by PS333")

# ----------------------------
# Inputs
# ----------------------------
prompt = st.text_area(
    "Enter your prompt",
    placeholder="E.g. A tiger meditating on a mountain peak, cinematic lighting, ultra detailed",
    height=110
)

negative = st.text_input(
    "Negative prompt (optional)",
    placeholder="E.g. blurry, low quality, watermark, extra fingers, bad anatomy"
)

style = st.selectbox(
    "Select Image Style",
    ["Realistic", "Photorealistic", "Cartoon", "Fantasy", "Cyberpunk", "Anime"]
)

with st.expander("⚙️ Advanced Settings", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        ratio = st.selectbox("Aspect Ratio Preset", list(RATIO_PRESETS.keys()))
        use_custom = st.checkbox("Use custom size", value=False)
    with col2:
        variations = st.slider("Variations", 1, 6, 4)
        seed_mode = st.selectbox("Seed Mode", ["Random", "Fixed"])

    if use_custom:
        w = st.number_input("Width", min_value=256, max_value=2048, value=RATIO_PRESETS[ratio][0], step=64)
        h = st.number_input("Height", min_value=256, max_value=2048, value=RATIO_PRESETS[ratio][1], step=64)
    else:
        w, h = RATIO_PRESETS[ratio]

    seed_value = None
    if seed_mode == "Fixed":
        seed_value = st.number_input("Seed (fixed)", min_value=0, max_value=999999, value=12345, step=1)

# ----------------------------
# Generate
# ----------------------------
btn_col1, btn_col2 = st.columns([1, 1])
with btn_col1:
    gen = st.button("✨ Generate Images", use_container_width=True)
with btn_col2:
    clear = st.button("🧹 Clear History", use_container_width=True)

if clear:
    st.session_state.history = []
    st.success("History cleared ✅")

if gen:
    if not prompt.strip():
        st.warning("Please enter a valid prompt.")
    else:
        final_prompt = build_prompt(style, prompt, negative)

        with st.spinner("⏳ Generating & downloading images..."):
            images_downloaded = []
            urls = []

            # If random seed mode, use different seeds each variation for unique results
            for i in range(variations):
                seed_i = seed_value
                if seed_mode == "Random":
                    # time-based seed-ish
                    seed_i = int(datetime.utcnow().timestamp() * 1000) % 1000000 + i

                url = pollinations_url(final_prompt, int(w), int(h), seed_i)
                urls.append((url, seed_i))

            # Download each image
            for idx, (url, s) in enumerate(urls, start=1):
                try:
                    img_bytes = fetch_image_bytes(url)
                    filename = f"ps333_{style.lower()}_{idx}_seed{s}.png"
                    images_downloaded.append((filename, img_bytes))

                    # push to history
                    st.session_state.history.insert(0, {
                        "url": url,
                        "prompt": final_prompt,
                        "style": style,
                        "w": int(w),
                        "h": int(h),
                        "seed": s,
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    st.error(f"Failed to fetch image #{idx}. Reason: {e}")

        # Show results
        if images_downloaded:
            st.success("✅ Images created! Ruko Zra Sabr Kro ✋")

            st.subheader("🖼️ Results")
            cols = st.columns(2)
            for i, (filename, img_bytes) in enumerate(images_downloaded):
                with cols[i % 2]:
                    st.image(img_bytes, use_container_width=True, caption=f"Generated by PS333 • {filename}")
                    st.download_button(
                        label="📥 Download",
                        data=img_bytes,
                        file_name=filename,
                        mime="image/png",
                        use_container_width=True
                    )

            # Download all ZIP
            zip_bytes = to_zip(images_downloaded)
            st.download_button(
                label="📦 Download All as ZIP",
                data=zip_bytes,
                file_name="ps333_images.zip",
                mime="application/zip",
                use_container_width=True
            )

# ----------------------------
# History & Favorites
# ----------------------------
st.markdown("---")
st.subheader("🕘 History")

if not st.session_state.history:
    st.info("No history yet. Generate some images first.")
else:
    # show latest 8 items
    for item in st.session_state.history[:8]:
        with st.container(border=True):
            st.caption(f"{item['ts']} • {item['style']} • {item['w']}x{item['h']} • seed={item['seed']}")
            st.write("**Prompt:** ", item["prompt"])
            colA, colB, colC = st.columns([2, 1, 1])
            with colA:
                st.image(item["url"], use_container_width=True)
            with colB:
                st.markdown(f"🔗 [Open Full Image]({item['url']})")
                try:
                    data = fetch_image_bytes(item["url"])
                    st.download_button(
                        "📥 Download",
                        data=data,
                        file_name=f"ps333_history_seed{item['seed']}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                except:
                    st.warning("Download not available right now.")
            with colC:
                if st.button("⭐ Save", key=f"fav_{item['ts']}_{item['seed']}"):
                    st.session_state.favorites.insert(0, item)
                    st.success("Saved to Favorites ✅")

st.subheader("⭐ Favorites")
if not st.session_state.favorites:
    st.info("No favorites saved yet.")
else:
    fav_cols = st.columns(2)
    for i, fav in enumerate(st.session_state.favorites[:6]):
        with fav_cols[i % 2]:
            st.image(fav["url"], use_container_width=True)
            st.caption(f"{fav['style']} • seed={fav['seed']}")
            st.markdown(f"🔗 [Open]({fav['url']})")

# ----------------------------
# Footer
# ----------------------------
st.markdown("---")
st.markdown(
    '🔧 Made with ❤️ by [**PS333**](https://instagram.com/prabhveersingh01) | 🔥 Powered by **PS333 AI Studio**'
)