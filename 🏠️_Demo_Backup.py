import streamlit as st


st.title('AI Fitness Trainer: Exercise Analysis')

# Exercise selection
exercise = st.radio('Select Exercise', ['Squats', 'Leg Raises'], horizontal=True)

if exercise == 'Squats':
    st.subheader('Squats Analysis Demo')
    recorded_file = 'output_sample.mp4'
    sample_vid = st.empty()
    sample_vid.video(recorded_file)
    
    st.markdown("""
    ### Squats Analysis Features:
    - Real-time pose detection and analysis
    - Form feedback for proper squat technique
    - Counter for correct and incorrect repetitions
    - Beginner and Pro difficulty modes
    - Live camera analysis and video upload options
    """)

elif exercise == 'Leg Raises':
    st.subheader('Leg Raises Analysis Demo')
    st.markdown("""
    ### Leg Raises Analysis Features:
    - Real-time pose detection for leg raise exercises
    - Form feedback for proper leg raise technique
    - Hold timer for sustained positions
    - Knee lock detection
    - Torso stability monitoring
    - Counter for correct and incorrect repetitions
    - Beginner and Pro difficulty modes
    - Live camera analysis and video upload options
    """)
    
    st.info("📹 Upload a video or use the live camera to analyze your leg raises!")

st.markdown("---")
st.markdown("### Navigation")
st.markdown("Use the sidebar to navigate between different analysis modes:")
st.markdown("- **📷️ Live Stream**: Real-time camera analysis")
st.markdown("- **⬆️ Upload Video**: Analyze pre-recorded videos")
