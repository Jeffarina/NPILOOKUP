import streamlit as st
import pandas as pd
import altair as alt
import time
from urllib.error import URLError
from urllib.request import urlopen, Request
import json
import time 



st.set_page_config(page_title="KMK HCP Crawler", page_icon="📊")

st.markdown("# KMK HCP Crawler Tool Demo")
st.sidebar.header("KMK HCP Crawler Tool Demo")
st.write(
    """This demo shows how to implement single/bulk look up for HCPs.
(Data courtesy of the [CMS.gov](https://npiregistry.cms.hhs.gov/search).)"""
)


@st.cache_data
def read_csv(file):
    data = pd.read_csv(file)
    return data


@st.cache_data
def convert_df(df):
   return df.to_csv(index=False).encode('utf-8')


# Create a function to preview a DataFrame
def preview_dataframe(df):
    st.write(df.head())


# Extract selective keys' values [ Including Nested Keys ]
# Using recursion + loop + yield
def get_vals(test_dict, key_list):
   for i, j in test_dict.items():
     if i in key_list:
        yield (i, j)
     yield from [] if not isinstance(j, dict) else get_vals(j, key_list)
 

def single_look_up(json_dict):
    basic_info_list = ['first_name', 'middle_name', 'last_name', 'credential', 'status']
    taxonomies_list = ['code', 'desc', 'license', 'state', 'primary']
    address_list= ['address_1', 'city', 'state', 'telephone_number']
    parents_list = ['addresses', 'taxonomies', "basic"]

    # pre-fix string
    merged_res_dict = {'NPI': json_dict['number'], 'ZIP': json_dict['addresses'][0]['postal_code'][0:5], 'LICENSE_STATE': json_dict['taxonomies'][0]['state']}

    # iteration parents_list
    for parent in parents_list: 
        if parent=='basic':
          merged_res_dict.update(dict(get_vals(json_dict[parent], basic_info_list)))
        elif parent=='addresses':
          merged_res_dict.update(dict(get_vals(json_dict[parent][0], address_list)))
        elif parent=='taxonomies':
          merged_res_dict.update(dict(get_vals(json_dict[parent][0], taxonomies_list)))  
    
    return merged_res_dict


def fetch_npi(npi_file):
    res_dict = {}
    res_dict_404 = []
    npis = npi_file['NPI'].tolist()
    pivot = 1
    pivot_end = len(npis)
    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text=progress_text)
    all_keys = set()
    
    for npi in npis:
        prog_index = int((pivot/pivot_end)*100)
        my_bar.progress(prog_index, text=f"Operation in progress. Please wait: {prog_index}%")
        pivot= pivot+1
        request = Request(f"https://npiregistry.cms.hhs.gov/api/?number={npi}&enumeration_type=&taxonomy_description=&name_purpose=&first_name=&use_first_name_alias=&last_name=&organization_name=&address_purpose=&city=&state=&postal_code=&country_code=&limit=&skip=&pretty=&version=2.1")
        response = urlopen(request)
        json_list = json.loads(response.read().decode('utf-8'))
        
        try: 
            json_dict = json_list['results'][0]
            to_add = single_look_up(json_dict)
            all_keys.update(to_add.keys())
            for key,val in to_add.items():
                if key not in res_dict:
                    res_dict[key] = []
                res_dict[key].append(val)

        except(IndexError):
            res_dict_404.append(npi)
            
    # Ensure all keys are present in res_dict and fill missing values with empty strings
    for key in all_keys:
        if key not in res_dict:
            res_dict[key] = [''] * len(npis)
        else:
            while len(res_dict[key]) < len(npis):
                res_dict[key].append('')

    my_bar.empty()
    return res_dict, res_dict_404


# Main
try: 
    # chat_box = st.chat_input("What do you want to do?")
    if "uploader_visible" not in st.session_state:
        st.session_state["uploader_visible"] = False
    def show_upload(state:bool):
        st.session_state["uploader_visible"] = state
    
    with st.chat_message("system"):
        cols= st.columns((3,1,1))
        cols[0].write("Do you want to upload a file?")
        cols[1].button("yes", use_container_width=True, on_click=show_upload, args=[True])
        cols[2].button("no", use_container_width=True, on_click=show_upload, args=[False])

    if st.session_state["uploader_visible"]:
        with st.chat_message("system"):
            uploaded_file = st.file_uploader("Upload your data")
            if uploaded_file:
                with st.spinner("Processing your file"):
                    time.sleep(5) #<- dummy wait for demo. 
                try: 
                    data = pd.read_csv(uploaded_file, dtype={'NPI': str})
                    row_count = data['NPI'].count()
                    st.write(f"File contains {row_count} NPIs")
                    preview_dataframe(data)
                    b = st.button('Generate', type='primary')
                    st.subheader("Output")
                    if b:
                        res_dict, res_dict_404 = fetch_npi(data)
                        res_df = pd.DataFrame(res_dict)
                        res_df.columns = [col.upper() for col in res_df.columns]
                        preview_dataframe(res_df)
                        res_csv = convert_df(res_df)
                        res_df_row_count = res_df['NPI'].count()
                        st.download_button(
                            f"Download {res_df_row_count} NPIs Found",
                            res_csv,
                            "NPIs Found.csv",
                            "text/csv",
                            key='download-res-csv'
                        )
                        res_404_df = pd.DataFrame(res_dict_404)
                        res_404_df.columns = [col.upper() for col in res_404_df.columns]
                        res_404_csv = convert_df(res_404_df)
                        if not res_404_df.empty:
                            res_404_df_row_count = res_404_df['NPI'].count()
                            st.download_button(
                                f"Download {res_404_df_row_count} NPIs Not Found",
                                res_404_csv,
                                "NPIs Not Found.csv",
                                "text/csv",
                                key='download-res-404-csv'
                            )

                except ValueError as e:
                    st.error(
                            """
                        **This demo requires csv format.**
                    """
                    )
                
    # df = get_UN_data()
    # attributes = st.multiselect(
    #     "Choose attributes", list(df.index), ["China", "United States of America"]
    # )
    # if not countries:
        # st.error("Please select at least one country.")
    # else:
        # data = df.loc[countries]
        # data /= 1000000.0
        # st.write("### Gross Agricultural Production ($B)", data.sort_index())

        # data = data.T.reset_index()
        # data = pd.melt(data, id_vars=["index"]).rename(
        #     columns={"index": "year", "value": "Gross Agricultural Product ($B)"}
        # )
        # chart = (
            # alt.Chart(data)
            # .mark_area(opacity=0.3)
            # .encode(
            #     x="year:T",
            #     y=alt.Y("Gross Agricultural Product ($B):Q", stack=None),
            #     color="Region:N",
            # )
        # )
        # st.altair_chart(chart, use_container_width=True)
except URLError as e:
    st.error(
        """
        **This demo requires internet access.**
        Connection error: %s
    """
        % e.reason
    )
