import xmltodict
import os
import json
import pandas as pd
import geopandas as gpd
import numpy as np
import pywaterml.waterML as pwml
import shapely.speedups

from .model import Groups, HydroServer_Individual


from tethys_sdk.permissions import has_permission

from .auxiliary import *
from .endpoints import available_regions_2, available_variables_2

from suds.client import Client  # For parsing WaterML/XML
from urllib.parse import unquote
from .endpoints import *
from django.http import JsonResponse
from .app import WaterDataExplorer as app
Persistent_Store_Name = 'catalog_db'


def available_regions(request):

    ret_object = {}
    list_regions = []
    SessionMaker = app.get_persistent_store_database(
        Persistent_Store_Name, as_sessionmaker=True)
    session = SessionMaker()

    region_list = []
    hydroserver_lat_list = []
    hydroserver_long_list = []
    hydroserver_name_list = []

    if request.method == 'POST' and 'group' not in request.POST:
        hydroservers_selected = session.query(HydroServer_Individual).all()
    else:
        specific_group=request.POST.get('group')
        hydroservers_selected = session.query(Groups).filter(Groups.title == specific_group)[0].hydroserver

    for server in hydroservers_selected:
        countries = json.loads(server.countries)['countries']
        region_list = region_list + list(set(countries) - set(region_list))

    ret_object['countries'] = region_list
    return JsonResponse(ret_object)

def available_variables(request):
    SessionMaker = app.get_persistent_store_database(
        Persistent_Store_Name, as_sessionmaker=True)
    session = SessionMaker()

    if request.method == 'POST' and 'group' not in request.POST:
        hydroservers_groups = session.query(HydroServer_Individual).all()
    else:
        specific_group=request.POST.get('group')
        hydroservers_groups = session.query(Groups).filter(Groups.title == specific_group)[0].hydroserver


    varaibles_list = {}
    hydroserver_variable_list = []
    hydroserver_variable_code_list = []
    hydroserver_urls_list = []
    hydroserver_server_list = []

    for server in hydroservers_groups:
        variables_server = json.loads(server.variables)

        hydroserver_variable_code_list = hydroserver_variable_code_list + variables_server['variables_codes']

        hydroserver_variable_list = hydroserver_variable_list + variables_server['variables']

        hydroserver_urls_list = hydroserver_urls_list + [server.url] * len(variables_server['variables'])
        hydroserver_server_list = hydroserver_server_list + [server.title] * len(variables_server['variables'])

    varaibles_list["variables"] = hydroserver_variable_list
    varaibles_list["variables_codes"] = hydroserver_variable_code_list
    varaibles_list['urls'] = hydroserver_urls_list
    varaibles_list['names'] = hydroserver_server_list

    return JsonResponse(varaibles_list)


######*****************************************************************************************################
######***********************CREATE AN EMPTY GROUP OF HYDROSERVERS ****************************################
######*****************************************************************************************################
def create_group(request):
    group_obj={}
    SessionMaker = app.get_persistent_store_database(Persistent_Store_Name, as_sessionmaker=True)
    session = SessionMaker()  # Initiate a session
    # Query DB for hydroservers
    if request.is_ajax() and request.method == 'POST':
        description = request.POST.get('textarea')

        title = request.POST.get('addGroup-title')
        url_catalog = request.POST.get('url')

        selected_services = []
        for key, value in request.POST.items():
            if value not in (title, description,url_catalog):
                selected_services.append(value.replace("_"," "))


        group_obj['title']= title
        group_obj['description']= description
        group_hydroservers=Groups(title=title, description=description)
        session.add(group_hydroservers)
        session.commit()
        session.close()

        if url_catalog:
            try:
                url_catalog = unquote(url_catalog)
                url_catalog2 = url_catalog + "?WSDL"
                water = pwml.WaterMLOperations(url = url_catalog2)
                services = water.GetWaterOneFlowServicesInfo()
                if selected_services:
                    views = water.aux._giveServices(services,selected_services)['working']
                    group_obj['views'] = addMultipleViews(request,hs_list=views,group = title)
                else:
                    views = water.aux._giveServices(services)['working']
                    group_obj['views'] = addMultipleViews(request,hs_list=views,group = title)

            except Exception as e:
                print(e)
                group_obj['views'] = []

    else:
        group_obj['message'] = 'There was an error while adding th group.'

    return JsonResponse(group_obj)



def addMultipleViews(request,hs_list,group):
    ret_object = []
    for hs in hs_list:
        new_url = hs['url']

        return_obj = {}
        try:
            sites_object = GetSites_WHOS(new_url)
            sites_parsed_json = json.dumps(sites_object)
            countries_json = json.dumps(available_regions_2(request,siteinfo = sites_parsed_json))

            variable_json = json.dumps(available_variables_2(hs['url']))
            return_obj['title'] = hs['title']
            return_obj['url'] = hs['url']
            return_obj['description'] = hs['description']
            return_obj['siteInfo'] = sites_parsed_json
            return_obj['group'] = group
            return_obj['status'] = "true"

            ret_object.append(return_obj)

            SessionMaker = app.get_persistent_store_database(
                Persistent_Store_Name, as_sessionmaker=True)
            session = SessionMaker()

            hydroservers_group = session.query(Groups).filter(Groups.title == group)[0]


            hs_one = HydroServer_Individual(title=hs['title'],
                             url=hs['url'],
                             description = hs['description'],
                             siteinfo=sites_parsed_json,
                             variables = variable_json,
                             countries = countries_json )

            hydroservers_group.hydroserver.append(hs_one)
            session.add(hydroservers_group)
            session.commit()
            session.close()

        #CHANGE LAST
        except Exception as detail:
            print(detail)
            continue


    return ret_object

######*****************************************************************************************################
######************RETRIEVES THE GROUPS OF HYDROSERVERS THAT WERE CREATED BY THE USER **********################
######*****************************************************************************************################

def get_groups_list(request):
    list_catalog = {}

    SessionMaker = app.get_persistent_store_database(Persistent_Store_Name, as_sessionmaker=True)

    session = SessionMaker()  # Initiate a session


    # Query DB for hydroservers
    hydroservers_groups = session.query(Groups).all()

    hydroserver_groups_list = []
    for group in hydroservers_groups:
        layer_obj = {}
        layer_obj["title"] = group.title
        layer_obj["description"] = group.description

        hydroserver_groups_list.append(layer_obj)

    list_catalog["hydroservers"] = hydroserver_groups_list

    list2={}
    array_example=[]
    for server in session.query(HydroServer_Individual).all():
        layer_obj = {}
        layer_obj["title"] = server.title
        layer_obj["url"] = server.url
        array_example.append(layer_obj)

    list2["servers"] =array_example

    return JsonResponse(list_catalog)

######*****************************************************************************************################
##############################LOAD THE HYDROSERVERS OF AN SPECIFIC GROUP#######################################
######*****************************************************************************************################
def catalog_group(request):

    specific_group=request.POST.get('group')

    list_catalog = {}

    SessionMaker = app.get_persistent_store_database(Persistent_Store_Name, as_sessionmaker=True)

    session = SessionMaker()  # Initiate a session
    hydroservers_group = session.query(Groups).filter(Groups.title == specific_group)[0].hydroserver
    h1=session.query(Groups).join("hydroserver")
    hs_list = []
    for hydroservers in hydroservers_group:
        name = hydroservers.title
        layer_obj = {}
        layer_obj["title"] = hydroservers.title
        layer_obj["url"] = hydroservers.url.strip()
        layer_obj["siteInfo"] = hydroservers.siteinfo
        hs_list.append(layer_obj)

    list_catalog["hydroserver"] = hs_list

    return JsonResponse(list_catalog)

######*****************************************************************************************################
############################## DELETE A GROUP OF HYDROSERVERS #############################
######*****************************************************************************************################

def delete_group(request):
    list_response = {}
    can_delete_permission = has_permission(request,"delete_hydrogroups")
    if can_delete_permission:
        list_catalog = {}
        list_groups ={}
        SessionMaker = app.get_persistent_store_database(
            Persistent_Store_Name, as_sessionmaker=True)
        session = SessionMaker()
        if request.is_ajax() and request.method == 'POST':
            groups=request.POST.getlist('groups[]')
            list_groups['groups']=groups
            list_response['groups']=groups
            i=0
            arrayTitles = []

            for group in groups:
                hydroservers_group = session.query(Groups).filter(Groups.title == group)[0].hydroserver
                for server in hydroservers_group:
                    title=server.title
                    arrayTitles.append(title)
                    i_string=str(i);
                    list_catalog[i_string] = title

                    i=i+1
                hydroservers_group = session.query(Groups).filter(Groups.title == group).first()
                session.delete(hydroservers_group)
                session.commit()
                session.close()
            list_response['hydroservers']=arrayTitles

    return JsonResponse(list_response)

def catalog_filter(request):
    ret_obj = {}
    actual_group = None
    if request.method == 'POST' and 'actual-group' in request.POST:
        actual_group = request.POST.getlist('actual-group')[0]
    countries = request.POST.getlist('countries')
    count_new = []
    var_new = []
    for count in countries:
        count_new.append(count.replace("_"," "))
    countries = count_new

    #PLEASE UNCOMMENT IN THE FUTURE##
    # variables = request.POST.getlist('variables')


    # for varia in variables:
    #     var_new.append(varia.replace("_"," "))
    # variables = var_new

    countries_geojson_file_path = os.path.join(app.get_app_workspace().path, 'countries3.geojson')
    countries_gdf = gpd.read_file(countries_geojson_file_path)
    selected_countries_plot = countries_gdf[countries_gdf['name_long'].isin(countries)].reset_index(drop=True)
    json_selected_country = selected_countries_plot.to_json()


    hs_filtered_region = filter_region(countries_geojson_file_path,countries, actual_group= actual_group)
    hs_filtered_variable = []
    #PLEASE UNCOMMENT IN THE FUTURE##
    # hs_filtered_variable = filter_variable(variables, actual_group=actual_group)
    list_columns_porsi = ["sitename", "latitude", "longitude", "sitecode", "url", "title"]
    array_sites_region = []
    array_sites_variables = []
    for part_sites in hs_filtered_region['stations']:
        array_sites_region.append(pd.DataFrame(part_sites['sites']))
    try:
        df_countries = pd.concat(array_sites_region).drop_duplicates().reset_index(drop=True)
    except Exception as e:
        df_countries = pd.DataFrame(columns = list_columns_porsi)

    for part_sites in hs_filtered_variable:
        array_sites_variables.append(pd.DataFrame(part_sites))

    try:
        df_vars = pd.concat(array_sites_variables).drop_duplicates().reset_index(drop=True)
    except Exception as e:
        df_vars = pd.DataFrame(columns = list_columns_porsi)

    df_final = pd.DataFrame()
    columns_list = list(df_vars.columns.values)
    if df_vars.empty and not df_countries.empty:
        df_final = df_countries
    if df_countries.empty and not df_vars.empty:
        df_final = df_vars
    if not df_countries.empty and not df_vars.empty:
        df_countries = df_countries.astype('str')
        df_vars = df_vars.astype('str')
        df_final = df_countries.merge(df_vars)

    final_obj_regions_vars = {}

    #create unique list of names
    uniqueNames = df_final.title.unique()
    uniqueHS = uniqueNames.tolist()

    #create a data frame dictionary to store your data frames
    DataFrameDict = {elem : pd.DataFrame for elem in uniqueNames}
    final_obj_regions_vars['hs'] = uniqueHS
    final_obj_regions_vars['stations'] = []
    for key in DataFrameDict.keys():
        temp_dict_sites = {}
        DataFrameDict[key] = df_final[:][df_final.title == key]
        dict_temp = DataFrameDict[key].to_dict('records')
        temp_dict_sites['sites'] = dict_temp
        temp_dict_sites['title'] = DataFrameDict[key]['title'].tolist()[0]
        temp_dict_sites['url'] = DataFrameDict[key]['url'].tolist()[0]
        final_obj_regions_vars['stations'].append(temp_dict_sites)
    final_obj_regions_vars['geojson'] = json_selected_country
    # print(final_obj_regions_vars)
    # print(df_final)


    # print("hs_filtered_region",hs_filtered_region)

    # Uncomment for filter varaible functionality #

    # print("hs_filtered_variable",hs_filtered_variable)
    # intersection_hs = []
    # if len(hs_filtered_region) > 0 and len(hs_filtered_variable) > 0:
    #     intersection_hs = list(set(hs_filtered_region) & set(hs_filtered_variable))
    # if len(hs_filtered_region) > 0:
    #     intersection_hs = hs_filtered_region
    # if len(hs_filtered_variable) > 0:
    #     intersection_hs = hs_filtered_variable
    # print(intersection_hs)
    # ret_obj['hs'] = intersection_hs


    # return JsonResponse(ret_obj)
    # return JsonResponse(hs_filtered_region)
    return JsonResponse(final_obj_regions_vars)


def filter_region(countries_geojson_file_path,list_countries, actual_group = None):
    region_list = []
    ret_object = {}
    if len(list_countries) > 0:
        shapely.speedups.enable()
        countries_gdf = gpd.read_file(countries_geojson_file_path)

        # countries_gdf2 = countries_gdf[countries_gdf['name'].isin(list_countries)]
        # countries_gdf2 = countries_gdf[countries_gdf['ADMIN'].isin(list_countries)]
        countries_gdf2 = countries_gdf[countries_gdf['admin'].isin(list_countries)]
        # countries_gdf2 = countries_gdf[countries_gdf['name_long'].isin(list_countries)]
        countries_series = countries_gdf2.loc[:,'geometry']
        SessionMaker = app.get_persistent_store_database(
            Persistent_Store_Name, as_sessionmaker=True)
        session = SessionMaker()
        hydroserver_lat_list = []
        hydroserver_long_list = []
        hydroserver_name_list = []
        hydroserver_country_list = []
        hydroserver_country_list_check = []
        hydroserver_siteInfo = []
        site_objInfo ={}

        servers = []
        if actual_group is None:
            hydroservers_selected = session.query(HydroServer_Individual).all()
        else:
            specific_group = actual_group
            hydroservers_selected = session.query(Groups).filter(Groups.title == specific_group)[0].hydroserver

        for server in hydroservers_selected:
            servers.append(server.title)
            sites = json.loads(server.siteinfo)
            ls_lats = []
            ls_longs = []
            site_names = []
            country_list_names = []
            country_list_names_check = []
            for site in sites:
                site_obj = {}
                ls_lats.append(site['latitude'])
                ls_longs.append(site['longitude'])
                site_names.append(site['fullSiteCode'])
                if(site['country'] != "No Data was Provided"):
                    country_list_names_check.append("country_metadata")
                country_list_names.append(site['country'])
                site_obj['country'] = site['country']
                site_obj['sitename'] = site['sitename']
                site_obj['latitude'] = site['latitude']
                site_obj['longitude'] = site['longitude']
                site_obj['network'] = site['network']
                site_obj['sitecode'] = site['sitecode']
                site_obj['url'] = server.url
                site_obj['title'] = server.title
                site_fullname_title = site['fullSiteCode'] + server.title
                site_objInfo[site_fullname_title] = site_obj

            hydroserver_lat_list.append(ls_lats)
            hydroserver_long_list.append(ls_longs)
            hydroserver_name_list.append(site_names)
            hydroserver_country_list.append(country_list_names)
            hydroserver_country_list_check.append(country_list_names_check)

        list_filtered = []
        list_countries_selected = []

        for indx in range(0,len(hydroserver_name_list)):
            if ("country_metadata" in hydroserver_country_list_check[indx]):
                list_countries_stations = {}
                list_countries_stations['title'] = hydroservers_selected[indx].title
                list_countries_stations['url'] = hydroservers_selected[indx].url
                list_countries_stations['sites'] = []

                df2 = pd.DataFrame({'SiteName': hydroserver_name_list[indx],'Country': hydroserver_country_list[indx]})
                if len(hydroserver_country_list[indx]) != len(hydroserver_name_list[indx]):
                    df2 = df2[df.Country != "No Data was Provided"]

                df_sites_within_countries = df2[df2['Country'].isin(list_countries)]
                if not df_sites_within_countries.empty:
                    sites_info_filter = []

                    for site_fullcode_single in df_sites_within_countries['SiteName'].tolist():
                        site_full_name = site_fullcode_single + hydroservers_selected[indx].title
                        sites_info_filter.append(site_objInfo[site_full_name])
                    list_countries_stations['sites'].extend(sites_info_filter)
                    region_list.append(hydroservers_selected[indx].title)
                    list_filtered.append(list_countries_stations)
            else:
                list_countries_stations = {}
                list_countries_stations['title'] = hydroservers_selected[indx].title
                list_countries_stations['url'] = hydroservers_selected[indx].url
                df = pd.DataFrame({'SiteName': hydroserver_name_list[indx],'Latitude': hydroserver_lat_list[indx],'Longitude': hydroserver_long_list[indx]})
                gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(df.Longitude, df.Latitude), index = hydroserver_name_list[indx])

                gdf = gdf.assign(**{str(key): gdf.within(geom) for key, geom in countries_series.items()})
                trues_onlys = gdf.copy()
                trues_onlys = trues_onlys.drop(['geometry'],axis=1)

                trues_onlys = trues_onlys.loc[:,trues_onlys.any()]
                trues_onlys_copy = trues_onlys.copy()

                countries_index = list(trues_onlys.columns)
                countries_index = [x for x in countries_index if x != 'geometry']
                countries_index2 = [int(i) for i in countries_index]
                countries_selected = countries_gdf.iloc[countries_index2]

                list_countries_selected = list(countries_selected['admin'])

                if len(list(countries_selected['admin'])) > 0:
                    region_list.append(hydroservers_selected[indx].title)
                    my_indx = 0
                    # print(trues_onlys_copy[countries_index])
                    list_countries_stations['sites'] = []
                    for column_ in trues_onlys_copy[countries_index]:
                        trues_onlys_copy[column_] = np.where(trues_onlys_copy[column_] == True, trues_onlys_copy.index, trues_onlys_copy[column_])
                        list_co = trues_onlys_copy[column_].tolist()
                        list_co = list(filter(lambda list_co: list_co != False, list_co))
                        # print("station codes ",len(list_co))
                        sites_info_filter = []
                        country_sel = list_countries_selected[my_indx]

                        for site_fullcode_single in list_co:
                            site_full_name = site_fullcode_single + hydroservers_selected[indx].title

                            site_objInfo[site_full_name]['country'] = country_sel

                            sites_info_filter.append(site_objInfo[site_full_name])

                        list_countries_stations['sites'].extend(sites_info_filter)
                        my_indx = my_indx + 1

                    list_filtered.append(list_countries_stations)
        ret_object['stations'] = list_filtered
        ret_object['hs'] = region_list
        return ret_object
    else:
        ret_object['stations'] = []
        ret_object['hs'] = []
        return ret_object


def filter_variable(variables_list, actual_group = None):

    hs_list = []
    if len(variables_list) > 0:
        list_catalog={}
        SessionMaker = app.get_persistent_store_database(Persistent_Store_Name, as_sessionmaker=True)
        session = SessionMaker()  # Initiate a session
        if actual_group is None:
            hydroservers_selected = session.query(HydroServer_Individual).all()
        else:
            specific_group = actual_group
            hydroservers_selected = session.query(Groups).filter(Groups.title == specific_group)[0].hydroserver
        hs_list = []
        for hydroservers in hydroservers_selected:
            # Safe Guard
            if "whos" in hydroservers.url:
                name = hydroservers.title
                hs_list_temp = []
                for variable_single in variables_list:
                    url2 = f'{hydroservers.url.strip().split("?")[0]}/GetSites?variableCode={variable_single}'
                    datos = requests.get(url2).content
                    sites_dict = xmltodict.parse(datos)
                    sites_json_object = json.dumps(sites_dict)
                    sites_json = json.loads(sites_json_object)['soap:Envelope']['soap:Body']['GetSitesResponse']['GetSitesResult']
                    sites_dict2 = xmltodict.parse(sites_json)
                    sites_json_object2 = json.dumps(sites_dict2)
                    sites_json2 = json.loads(sites_json_object2)
                    try:
                        hs_sites = []
                        if "sitesResponse" in sites_json2:
                            sites_object = sites_json2['sitesResponse']['site']

                            # If statement is executed for multiple sites within the HydroServer, if there is a single site then it goes to the else statement
                            # Parse through the HydroServer and each site with its metadata as a
                            # dictionary object to the hs_sites list
                            if type(sites_object) is list:
                                for site in sites_object:
                                    hs_json = {}
                                    latitude = site['siteInfo']['geoLocation'][
                                        'geogLocation']['latitude']
                                    longitude = site['siteInfo']['geoLocation'][
                                        'geogLocation']['longitude']
                                    site_name = site['siteInfo']['siteName']
                                    site_name = site_name.encode("utf-8")
                                    network = site['siteInfo']['siteCode']["@network"]
                                    sitecode = site['siteInfo']['siteCode']["#text"]

                                    hs_json["sitename"] = site_name.decode("UTF-8")
                                    hs_json["latitude"] = latitude
                                    hs_json["longitude"] = longitude
                                    hs_json["sitecode"] = sitecode
                                    hs_json["network"] = network
                                    hs_json["url"] = hydroservers.url
                                    hs_json["title"] = hydroservers.title
                                    hs_sites.append(hs_json)
                            else:
                                hs_json = {}
                                latitude = sites_object['siteInfo'][
                                    'geoLocation']['geogLocation']['latitude']
                                longitude = sites_object['siteInfo'][
                                    'geoLocation']['geogLocation']['longitude']
                                site_name = sites_object['siteInfo']['siteName']
                                site_name = site_name.encode("utf-8")
                                network = sites_object['siteInfo']['siteCode']["@network"]
                                sitecode = sites_object['siteInfo']['siteCode']["#text"]

                                hs_json["sitename"] = site_name.decode("UTF-8")
                                hs_json["latitude"] = latitude
                                hs_json["longitude"] = longitude
                                hs_json["sitecode"] = sitecode
                                hs_json["network"] = network
                                hs_json["url"] = hydroservers.url
                                hs_json["title"] = hydroservers.title
                                hs_sites.append(hs_json)


                        sites_object = hs_sites
                        df = pd.DataFrame.from_dict(sites_object)
                        hs_list_temp.append(df)
                    except Exception as e:
                        print(e)
                try:
                    df_temp = pd.concat(hs_list_temp).drop_duplicates().reset_index(drop=True)
                    dict_temp = df_temp.to_dict('records')

                    hs_list.append(dict_temp)
                except ValueError as e:
                    print(e)


    return hs_list

def get_variables_for_country(request):
    response_obj = {}
    countries = request.POST.getlist('countries[]')
    list_variables = []
    list_variables_codes = []

    SessionMaker = app.get_persistent_store_database(Persistent_Store_Name, as_sessionmaker=True)
    session = SessionMaker()

    hydroservers_selected = session.query(HydroServer_Individual).all()
    for hs_selected in hydroservers_selected:
        list_contries_final = json.loads(hs_selected.countries)['countries']
        set_contries_final = set(list_contries_final)
        set_request_final = set(countries)

        if (set_contries_final & set_request_final):
            hs_variables_json  = json.loads(hs_selected.variables)
            list_variables = list_variables + hs_variables_json['variables']
            list_variables_codes = list_variables_codes +hs_variables_json['variables_codes']

    response_obj['variables'] = list_variables
    response_obj['variables_codes'] = list_variables_codes
    return JsonResponse(response_obj)

######*****************************************************************************************################
############################## Function to retrieve the keywords for all the selected groups #############################
######*****************************************************************************************################
def keyWordsForGroup(request):
    list_catalog={}
    specific_group=request.POST.get('group')

    SessionMaker = app.get_persistent_store_database(Persistent_Store_Name, as_sessionmaker=True)

    session = SessionMaker()  # Initiate a session
    hydroservers_group = session.query(Groups).filter(Groups.title == specific_group)[0].hydroserver
    hs_list = []
    words_to_search={};

    for hydroservers in hydroservers_group:
        name = hydroservers.title
        layer_obj = {}
        layer_obj["title"] = hydroservers.title
        layer_obj["url"] = hydroservers.url.strip()
        layer_obj["siteInfo"] = hydroservers.siteinfo
        client = Client(url = hydroservers.url.strip(), timeout= 500)

        keywords = client.service.GetVariables('[:]')

        keywords_dict = xmltodict.parse(keywords)
        keywords_dict_object = json.dumps(keywords_dict)

        keywords_json = json.loads(keywords_dict_object)
        array_variables=keywords_json['variablesResponse']['variables']['variable']
        array_keywords_hydroserver=[]

        if isinstance(array_variables,type([])):
            for words in array_variables:
                array_keywords_hydroserver.append(words['variableName'])
        if isinstance(array_variables,dict):
            array_keywords_hydroserver.append(array_variables['variableName'])

        words_to_search[name] = array_keywords_hydroserver

        hs_list.append(layer_obj)

    list_catalog["hydroserver"] = hs_list
    list_catalog["keysSearch"] = words_to_search

    return JsonResponse(list_catalog)
