import streamlit as st
import os
import cv2
import numpy as np
import easyocr
import re
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker




st.title("Business Card Text Extraction")


# Function to overlay text on the image
def overlay_text(image, res):
    for (bbox, text, prob) in res:
        # Unpack the bounding box
        (tl, tr, br, bl) = bbox
        tl = (int(tl[0]), int(tl[1]))
        tr = (int(tr[0]), int(tr[1]))
        br = (int(br[0]), int(br[1]))
        bl = (int(bl[0]), int(bl[1]))

        # Draw a rectangle around the text
        image = cv2.rectangle(image, tl, br, (0, 255, 0), 2)

        # Draw the text above the rectangle
        cv2.putText(image, text, (tl[0], tl[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0),2) 
                    
    return image

# Function to extract text from the uploaded image
def extract_text_from_image(uploaded_card):
    # Create "uploaded_cards" directory if it doesn't exist
    if not os.path.exists("uploaded_cards"):
        os.makedirs("uploaded_cards")

    saved_img = os.path.join("uploaded_cards", uploaded_card.name)
    with open(saved_img, "wb") as f:
        f.write(uploaded_card.getbuffer())

    image = cv2.imread(saved_img)
    reader = easyocr.Reader(['en'])  # Specify the language here if required
    res = reader.readtext(saved_img)

    return image, res

def extract_data(res):
    extracted_data = {
        "company_name": "",
        "card_holder": "",
        "designation": "",
        "mobile_number": [],
        "email": "",
        "website": "",
        "area": "",
        "city": "",
        "state": "",
        "pin_code": [],
    }

    for i, text_info in enumerate(res):
        text = text_info[1]  # Extract the text from the tuple
        prob = text_info[2]  # Extract the probability from the tuple

        # To get WEBSITE_URL
        if "www " in text.lower() or "www." in text.lower():
            extracted_data["website"] = text
        elif "WWW" in text:
            extracted_data["website"] = res[4][1] + "." + res[5][1]

        # To get EMAIL ID
        elif "@" in text:
            extracted_data["email"] = text

        # To get MOBILE NUMBER
        elif "-" in text:
            extracted_data["mobile_number"].append(text)
            if len(extracted_data["mobile_number"]) == 2:
                extracted_data["mobile_number"] = " & ".join(extracted_data["mobile_number"])

        elif i == len(res) - 1:
            if extracted_data["company_name"]:
                extracted_data["company_name"] += " " + text
            else:
                extracted_data["company_name"] = text

        # To get CARD HOLDER NAME
        elif i == 0:
            extracted_data["card_holder"] = text

        # To get DESIGNATION
        elif i == 1:
            extracted_data["designation"] = text

        # To get AREA
        if re.findall("^[0-9].+, [a-zA-Z]+", text):
            extracted_data["area"] = text.split(",")[0]
        elif re.findall("[0-9] [a-zA-Z]+", text):
            extracted_data["area"] = text

        # To get CITY NAME
        match1 = re.findall(".+St , ([a-zA-Z]+).+", text)
        match2 = re.findall(".+St,, ([a-zA-Z]+).+", text)
        match3 = re.findall("^[E].*", text)
        if match1:
            extracted_data["city"] = match1[0]
        elif match2:
            extracted_data["city"] = match2[0]
        elif match3:
            extracted_data["city"] = match3[0]

        # To get STATE
        state_match = re.findall("[a-zA-Z]{9} +[0-9]", text)
        if state_match:
            extracted_data["state"] = text[:9]
        elif re.findall("^[0-9].+, ([a-zA-Z]+);", text):
            extracted_data["state"] = text.split()[-1]
        if len(extracted_data["state"]) == 2:
            extracted_data["state"].pop(0)

        # To get PINCODE
        if len(text) >= 6 and text.isdigit():
            extracted_data["pin_code"].append(text)
        elif re.findall("[a-zA-Z]{9} +[0-9]", text):
            extracted_data["pin_code"].append(text[10:])

    return extracted_data


Base = declarative_base()

# Define the table schema
class Image(Base):
    __tablename__ = 'image'
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String)
    card_holder = Column(String)
    designation = Column(String)
    mobile_number = Column(String)
    email = Column(String)
    website = Column(String)
    area = Column(String)
    city = Column(String)
    state = Column(String)
    pin_code = Column(String)


def save_to_postgresql(extracted_data):
    # Set up the PostgreSQL database connection
    username = "postgres"
    password = "12345"
    host = "localhost"
    port = "5432"
    database_name = "guvi"
    engine = create_engine(f'postgresql://{username}:{password}@{host}:{port}/{database_name}')

    # Create the table if it does not exist
    Base.metadata.create_all(engine)

    # Create a session to interact with the database
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create a new Image object and add it to the session
    image_entry = Image(
        company_name=extracted_data["company_name"],
        card_holder=extracted_data["card_holder"],
        designation=extracted_data["designation"],
        mobile_number=extracted_data["mobile_number"],
        email=extracted_data["email"],
        website=extracted_data["website"],
        area=extracted_data["area"],
        city=extracted_data["city"],
        state=extracted_data["state"],
        pin_code=extracted_data["pin_code"]
    )
    session.add(image_entry)

    # Commit the changes to the database
    session.commit()
    session.close()

def main():
    ##st.title("Business Card Text Extraction and Saving to PostgreSQL")

    selected = st.selectbox("Select an option:", ["Upload & Extract"])

    if selected == "Upload & Extract":
        st.markdown("### Upload a Business Card")
        uploaded_card = st.file_uploader("Upload here", label_visibility="collapsed", type=["png", "jpeg", "jpg"])

        if uploaded_card is not None:
            if st.button("Process and Extract Text"):
                with st.spinner("Please wait, processing image..."):
                    # Get the image and OCR results
                    image, res = extract_text_from_image(uploaded_card)

                st.markdown("### Image Processed and Text Extracted")

                # Display the image with overlaid text
                overlayed_image = overlay_text(np.copy(image), res)
                st.image(overlayed_image, caption="Text Extraction Result", channels="BGR")

                # Extract data from the OCR result
                extracted_data = extract_data(res)

                # Pre-fill the text input widgets with extracted values
                st.text_area("Company_Name", extracted_data["company_name"])
                st.text_input("Card_Holder", extracted_data["card_holder"])
                st.text_input("Designation", extracted_data["designation"])
                st.text_area("Mobile_Number", extracted_data["mobile_number"])
                st.text_input("Email", extracted_data["email"])
                st.text_input("Website", extracted_data["website"])
                st.text_input("Area", extracted_data["area"])
                st.text_input("City", extracted_data["city"])
                st.text_input("State", extracted_data["state"])
                st.text_input("Pin_Code", extracted_data["pin_code"])

                # Save the data to PostgreSQL on button click
                if st.button("Save to PostgreSQL"):
                    save_to_postgresql(extracted_data)
                    st.success("Data saved to PostgreSQL!")

if __name__ == "__main__":
    main()
