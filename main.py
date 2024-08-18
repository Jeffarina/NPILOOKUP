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
                st.write(f"File contains {row_count} NPIs (Preview)")
                preview_dataframe(data)

                # Mapping of user-friendly names to original attribute names
                attribute_mapping = {
                    'NPI': 'NPI',
                    'ZIP': 'ZIP',
                    'License_State': 'LICENSE_STATE',
                    'First Name': 'first_name',
                    'Middle Name': 'middle_name',
                    'Last Name': 'last_name',
                    'Credential': 'credential',
                    'Status': 'status',
                    'Taxonomy Code': 'code',
                    'Specialty': 'desc',
                    'License': 'license',
                    'Address 1': 'address_1',
                    'City': 'city',
                    'State': 'state',
                    'Primary Address 1': 'primary_address_1',
                    'Primary City': 'primary_city',
                    'Primary State': 'primary_state',
                    'Primary ZIP': 'primary_zip',
                    'Secondary Address 1': 'secondary_address_1',
                    'Secondary City': 'secondary_city',
                    'Secondary State': 'secondary_state',
                    'Secondary ZIP': 'secondary_zip'
                }

                # Reverse mapping for displaying the DataFrame
                reverse_attribute_mapping = {v: k for k, v in attribute_mapping.items()}

                # Dropdown for address option
                address_option = st.selectbox(
                    "Select address option",
                    ["Single address per NPI", "Multiple addresses per NPI"]
                )
                single_address_flag = address_option == "Single address per NPI"

                # Define attributes based on the address option
                attributes_single_address = ['NPI', 'ZIP', 'License_State', 'First Name', 'Middle Name', 'Last Name', 'Credential', 'Status', 'Taxonomy Code', 'Specialty', 'License', 'Address 1', 'City', 'State']
                attributes_multiple_addresses = ['NPI', 'License_State', 'First Name', 'Middle Name', 'Last Name', 'Credential', 'Status', 'Taxonomy Code', 'Specialty', 'License', 'Primary Address 1', 'Primary City', 'Primary State', 'Primary ZIP', 'Secondary Address 1', 'Secondary City', 'Secondary State', 'Secondary ZIP']

                # Conditional display of attributes
                if single_address_flag:
                    attributes = st.multiselect(
                        "Select attributes to include",
                        attributes_single_address,
                        default=attributes_single_address)
                else:
                    attributes = st.multiselect(
                        "Select attributes to include",
                        attributes_multiple_addresses,
                        default=attributes_multiple_addresses)

                # Map user-friendly names to original attribute names for fetch_npi
                selected_attributes = [attribute_mapping[attr] for attr in attributes]

                b = st.button('Generate', type='primary')
                st.subheader("Output")
                if b:
                    res_dict_result, res_dict_404_result = fetch_npi(data, selected_attributes, single_address_flag)
                    res_df = pd.DataFrame(res_dict_result)
                    res_df.columns = [col.upper() for col in res_df.columns]
                    
                    # Remove rows where the NPI column is empty or contains empty strings
                    res_df = res_df.dropna(subset=['NPI'])
                    res_df = res_df[res_df['NPI'].str.strip() != '']
                    
                    # Transform columns back to user-friendly names
                    res_df.columns = [reverse_attribute_mapping.get(col.lower(), col) for col in res_df.columns]
                    
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
                    res_404_df = pd.DataFrame(res_dict_404_result, columns=['NPI'])
                    res_404_df.columns = [col.upper() for col in res_404_df.columns]
                    res_404_csv = convert_df(res_404_df)
                    if not res_404_df.empty:
                        res_404_df_row_count = res_404_df['NPI'].count()
                        preview_dataframe(res_404_df)
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

except URLError as e:
    st.error(
        """
        **This demo requires internet access.**
        Connection error: %s
    """
        % e.reason
    )
