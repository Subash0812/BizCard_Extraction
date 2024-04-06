#-------------------------------------------------Import Needed Libraries--------------------------------------------------
import pandas as pd
import re
from PIL import Image 
import easyocr
import streamlit as st
import numpy as np
import cv2
import mysql.connector

#--------------------------------------------------EasyOCR Reader-------------------------------------------------------------
reader = easyocr.Reader(['en'],gpu=False)

# config = {
#     'host':'database-1.cp40yqs0ismt.ap-south-1.rds.amazonaws.com',
#     'user':'admin',   'password':'root2012', 'database':'bizcard'
# }
# mydb = mysql.connector.connect(**config)


#---------------------------------------------------MySQL Connection------------------------------------------------------
config = {
    'host':'127.0.0.1',     'user':'root',
    'password':'1234',      'database':'bizcard'
}
mydb = mysql.connector.connect(**config)
cursor = mydb.cursor()

query = """CREATE TABLE IF NOT EXISTS card 
            (company_id INTEGER PRIMARY KEY AUTO_INCREMENT,
             company_name Varchar(150),
             card_holder_name varchar(150),
             designation varchar(150),
             mobile_number varchar(150),
             email varchar(150),
             website varchar(150),
             area text,
             city varchar(150),
             state varchar(150),
             pincode varchar(10),
             image LONGBLOB);"""
cursor.execute(query)



#-------------------------------------------Text detection from image--------------------------------------------------
def text_detection(img):
    result = reader.readtext(img,paragraph=False)
    for i in range(len(result)):
        top_left = result[i][0][0]
        bottom_right = result[i][0][2]
        ad = (-235,25)
        res = tuple(map(lambda i,j:i+j,bottom_right,ad))
        text = result[i][1]
        font = cv2.FONT_HERSHEY_PLAIN
        img = cv2.rectangle(img,(int(top_left[0]),int(top_left[1])),(int(bottom_right[0]),int(bottom_right[1])),(255,100,3),3)
        img = cv2.putText(img,text,(int(res[0]),int(res[1])),font,2.0,(255,170,51),3,cv2.LINE_AA)
    return st.image(img,width=450,caption='Captured Text')


#-----------------------------------Function used for converting image to binary format---------------------------------
def img_to_binary(img):
    image = Image.open(img)
    img_array = np.array(image)  
    return img_array 
print()


#--------------------------------------------Getting Data From Biz Card-------------------------------------------------
def get_data(result):
    for ind,i in enumerate(result):
        if 'www' in i.lower() or 'www.' in i.lower():
            data['website'].append(i)
        elif 'WWW' in i:
            data['website']=result[4]+'.'+result[5]  
        elif '-' in i:
            data['mobile_number'].append(i)
            if len(data['mobile_number'])==2:
                data['mobile_number'] = ' & '.join(data['mobile_number'])
        elif '@' in i:
            data['email'].append(i)
        elif ind == len(result)-1:
            data['company_name'].append(i)
        elif ind == 0:
            data['card_holder_name'].append(i)
        elif ind == 1:
            data['designation'].append(i)

        if re.findall('^[0-9].+, [a-zA-Z]+',i):
                data["area"].append(i.split(',')[0])
        elif re.findall('[0-9] [a-zA-Z]+',i):
                data["area"].append(i)

                
        match1 = re.findall('.+St , ([a-zA-Z]+).+', i)
        match2 = re.findall('.+St,, ([a-zA-Z]+).+', i)
        match3 = re.findall('^[E].*',i)
        if match1:
            data["city"].append(match1[0])
        elif match2:
            data["city"].append(match2[0])
        elif match3:
            data["city"].append(match3[0])

        state_match = re.findall('[a-zA-Z]{9} +[0-9]',i)
        if state_match:
                data["state"].append(i[:9])
        elif re.findall('^[0-9].+, ([a-zA-Z]+);',i):
            data["state"].append(i.split()[-1])
        if len(data["state"])== 2:
            data["state"].pop(0)

        if len(i)>=6 and i.isdigit():
            data["pincode"].append(i)
        elif re.findall('[a-zA-Z]{9} +[0-9]',i):
            data["pincode"].append(i[10:])                             



st.title(':orange[Biz Card Data Extraction]')
tab1,tab2 = st.tabs(['Data Extraction','Data Modification'])


#------------------------------------------------Data Exraction Zone--------------------------------------------------------
with tab1:
    file = st.file_uploader('Upload a Biz Card pic',type=['png','jpg'],accept_multiple_files=False)
    if file is not None:
        image_bytes = file.read()
        image_array = np.frombuffer(image_bytes, np.uint8)
        pic = cv2.imdecode(image_array,cv2.IMREAD_COLOR)
        img = cv2.imdecode(image_array,cv2.IMREAD_COLOR)
        data = {
                'company_name':[],
                'card_holder_name': [],
                'designation':[],
                'mobile_number':[],
                'email':[],
                'website':[],
                'area':[],
                'city':[],
                'state':[],
                'pincode':[],
                'image': str(img_to_binary(file))
            } 
        col1,col2,col3 = st.columns(3)
        with col1:
            st.image(img,width=450)
        with col2:
            pass
        with col3:    
            text_detection(img)

        forre = reader.readtext(pic,detail=0,paragraph=False)
        get_data(forre)
        df = pd.DataFrame(data)
        st.dataframe(df)

        if st.button('Upload Data to Data Base'):
            for i,row in df.iterrows(): 
                query = """INSERT INTO card(company_name,card_holder_name,designation,mobile_number,email,website,area,city,state,pincode,image)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                cursor.execute(query, tuple(row))
                mydb.commit()
            st.success("Data Uploaded Successfully")



#--------------------------------------------------Data Manipulation Zone------------------------------------------------------           
with tab2:
    col1,col2 = st.columns(2)
    with col1:
        st.markdown('### :blue[Update Menu]') 
        cursor.execute("SELECT card_holder_name FROM card")
        rows = cursor.fetchall()
        names = []
        for row in rows:
            names.append(row[0])
        card_holder = st.selectbox('Choose a card holder name',names,key='card_holder')
        cursor.execute("SELECT * FROM card WHERE card_holder_name=%s", (card_holder,))
        col_data = cursor.fetchone()

        Company_name = st.text_input("Company name", col_data[1])
        Card_holder = st.text_input("Card Holder Name", col_data[2])
        Designation = st.text_input("Designation", col_data[3])
        Mobile_number = st.text_input("Mobile number", col_data[4])
        Email = st.text_input("Email", col_data[5])

    with col2:
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        Website = st.text_input("Website", col_data[6])
        Area = st.text_input("Area", col_data[7])
        City = st.text_input("City", col_data[8])
        State = st.text_input("State", col_data[9])
        Pin_code = st.text_input("Pincode", col_data[10])    
        
        update = st.button('Update', key = 'update')
        if update:
            cursor.execute(
                    "UPDATE card SET company_name = %s, designation = %s, mobile_number = %s, email = %s, "
                    "website = %s, area = %s, city = %s, state = %s, pincode = %s "
                    "WHERE card_holder_name=%s",
                    (Company_name, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code, card_holder))
                
            mydb.commit()
            st.success('Data Successfully Updated to the database')


    st.write('')
    st.markdown('### :blue[Delete Menu]')
    delete_name = st.selectbox("Select a Card holder name to Delete", names, key='delete_name')
    delete = st.button('Delete', key = 'delete')    

    if delete:
        cursor.execute(f"DELETE FROM card WHERE card_holder_name='{delete_name}'")
        mydb.commit()
        mydb.close()
        st.success("Data Successfully deleted from the database.")    