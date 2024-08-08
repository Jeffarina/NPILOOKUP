import streamlit as st
import pandas as pd
from urllib.error import URLError
from urllib.request import urlopen, Request
import json
import time

# Constants
API_URL = "https://npiregistry.cms.hhs.gov/api/?number={npi}&enumeration_type=&taxonomy_description=&name_purpose=&first_name=&use_first_name_alias=&last_name=&organization_name=&address_purpose=&city=&state=&postal_code=&country_code=&limit=&skip=&pretty=&version=2.1"

# Streamlit Configuration
st.set_page_config(page_title="KMK HCP Crawler", page_icon="📊")
st.markdown("# KMK HCP Crawler Tool Demo")
st.sidebar.header("KMK HCP Crawler Tool Demo")
st.write("""This demo shows how to implement single/bulk look up for HCPs.
(Data courtesy of the [CMS.gov](https://npiregistry.cms.hhs.gov/search).)""")


# Caching Functions
@st.cache_data
def read_csv(file):
    return pd.read_csv(file)


@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')


# Helper Functions
def preview_dataframe(df):
    st.write(df.head())


def get_vals(test_dict, key_list):
    for i, j in test_dict.items():
        if i in key_list:
            yield i, j
        yield from [] if isinstance(j, dict) else get_vals(j, key_list)


def single_look_up(json_dict, selected_attributes, single_address):
    basic_info_list = ['first_name', 'middle_name', 'last_name', 'credential', 'status']
    taxonomies_list = ['code', 'desc', 'license', 'state', 'primary']
    address_list = ['address_1', 'city', 'state', 'telephone_number']
    parents_list = ['addresses', 'taxonomies', "basic"]

    merged_res_dict = {
        'NPI': json_dict['number'],
        'ZIP': json_dict['addresses'][0]['postal_code'][0:5],
        'LICENSE_STATE': json_dict['taxonomies'][0]['state']
    }

    for parent in parents_list:
        if parent == 'basic':
            merged_res_dict.update(dict(get_vals(json_dict[parent], basic_info_list)))
        elif parent == 'addresses':
            primary_address = dict(get_vals(json_dict[parent][0], address_list))
            merged_res_dict.update({f'primary_{k}': v for k, v in primary_address.items()})
            if not single_address and len(json_dict[parent]) > 1:
                secondary_address = dict(get_vals(json_dict[parent][1], address_list))
                if primary_address == secondary_address:
                    for key in address_list:
                        merged_res_dict[f'secondary_{key}'] = ''
                else:
                    merged_res_dict.update({f'secondary_{k}': v for k, v in secondary_address.items()})
            else:
                for key in address_list:
                    merged_res_dict[f'secondary_{key}'] = ''
        elif parent == 'taxonomies':
            merged_res_dict.update(dict(get_vals(json_dict[parent][0], taxonomies_list)))

    filtered_res_dict = {k: v for k, v in merged_res_dict.items() if k in selected_attributes}
    return filtered_res_dict


def fetch_npi(npi_file, selected_attributes, single_address):
    res_dict = {}
    res_dict_404 = []
    npis = npi_file['NPI'].tolist()
    pivot = 1
    pivot_end = len(npis)
    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text=progress_text)
    all_keys = set()

   for npi in npis:
        prog_index = int((pivot / pivot_end) * 100)
        my_bar.progress(prog_index, text=f"Operation in progress. Please wait: {prog_index}%")
        pivot += 1
        request = Request(API_URL.format(npi=npi))
        response = urlopen(request)
        json_list = json.loads(response.read().decode('utf-8'))
        try:
            json_dict = json_list['results'][0]
            to_add = single_look_up(json_dict, selected_attributes, single_address)
            all_keys.update(to_add.keys())
            for key, val in to_add.items():
                if key not in res_dict:
                    res_dict[key] = []
                res_dict[key].append(val)
        except IndexError:
            res_dict_404.append(npi)

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
    if "uploader_visible" not in st.session_state:
        st.session_state["uploader_visible"] = False

    def show_upload(state: bool):
        st.session_state["uploader_visible"] = state

    if st.button("Upload", use_container_width=True, on_click=show_upload, args=[True]):
        st.session_state["uploader_visible"] = True

    if st.session_state["uploader_visible"]:
        uploaded_file = st.file_uploader("Upload your data")
        if uploaded_file:
            with st.spinner("Processing your file"):
                time.sleep(5)  # <- dummy wait for demo.
            try:
                data = pd.read_csv(uploaded_file, dtype={'NPI': str})
                row_count = data['NPI'].count()
                st.write(f"File contains {row_count} NPIs")
                preview_dataframe(data)

                address_option = st.selectbox(
                    "Select address option",
                    ["Single address per NPI", "Multiple addresses per NPI"]
                )
                single_address = address_option == "Single address per NPI"

                attributes = st.multiselect(
                    "Select attributes to include",
                    ['NPI', 'ZIP', 'LICENSE_STATE', 'first_name', 'middle_name', 'last_name', 'credential', 'status',
                     'code', 'desc', 'license', 'state', 'primary', 'address_1', 'city', 'telephone_number', 
                     'primary_address_1', 'primary_city', 'primary_state', 'primary_zip', 'secondary_address_1', 
                     'secondary_city', 'secondary_state', 'secondary_zip']
                )

                if st.button('Generate', type='primary'):
                    res_dict, res_dict_404 = fetch_npi(data, attributes, single_address)
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
                st.error("**This demo requires csv format.**")

except URLError as e:
    st.error(f"**This demo requires internet access.**\nConnection error: {e.reason}")

 
