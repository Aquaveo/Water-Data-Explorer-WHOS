from tethys_sdk.app_settings import (
    CustomSetting,
    PersistentStoreDatabaseSetting,
    SpatialDatasetServiceSetting,
)
from tethys_sdk.base import TethysAppBase, url_map_maker
from tethys_sdk.permissions import Permission, PermissionGroup


class WaterDataExplorer(TethysAppBase):
    """
    Tethys app class for Water Data Explorer.
    """

    name = "Water Data Explorer"
    index = "water_data_explorer_whos:home"
    icon = "water_data_explorer_whos/images/wde.png"
    package = "water_data_explorer_whos"
    root_url = "water-data-explorer-whos"
    color = "#868e96"
    description = (
        '"A tethys app that lets the user to visualize and query WSDL enpoints'
    )
    tags = '"Hydrology", "WMO", "BYU"'
    enable_feedback = False
    feedback_emails = []

    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (
            UrlMap(
                name="home",
                url="water-data-explorer-whos",
                controller="water_data_explorer_whos.startAll.home",
            ),
            UrlMap(
                name="create-group",
                url="create-group/",
                controller="water_data_explorer_whos.groups.create_group",
            ),
            UrlMap(
                name="load-groups",
                url="load-groups/",
                controller="water_data_explorer_whos.groups.get_groups_list",
            ),
            UrlMap(
                name="add-hydrosever-groups",
                url="soap-group/",
                controller="water_data_explorer_whos.endpoints.soap_group",
            ),
            UrlMap(
                name="update-hydrosever-groups",
                url="soap-update/",
                controller="water_data_explorer_whos.endpoints.upload_hs",
            ),
            UrlMap(
                name="save-sites",
                url="save-sites/",
                controller="water_data_explorer_whos.endpoints.save_sites_data",
            ),
            UrlMap(
                name="save-new-sites",
                url="save_new_sites/",
                controller="water_data_explorer_whos.endpoints.save_new_sites_data",
            ),
            UrlMap(
                name="save-stream",
                url="save_stream/",
                controller="water_data_explorer_whos.endpoints.save_only_sites_stream",
            ),
            UrlMap(
                name="save-variables",
                url="save-variables/",
                controller="water_data_explorer_whos.endpoints.save_variables_data",
            ),
            UrlMap(
                name="load-hydroserver-of-groups",
                url="catalog-group/",
                controller="water_data_explorer_whos.groups.catalog_group",
            ),
            UrlMap(
                name="delete-group-hydroserver",
                url="delete-group-hydroserver/",
                controller="water_data_explorer_whos.endpoints.delete_group_hydroserver",
            ),
            UrlMap(
                name="delete-group",
                url="delete-group/",
                controller="water_data_explorer_whos.groups.delete_group",
            ),
            UrlMap(
                name="keyword-group",
                url="keyword-group",
                controller="water_data_explorer_whos.groups.keyWordsForGroup",
            ),
            UrlMap(
                name="get-variables-hs",
                url="get-variables-hs/",
                controller="water_data_explorer_whos.endpoints.get_variables_hs",
            ),
            UrlMap(
                name="get-available-sites",
                url="get-available-sites/",
                controller="water_data_explorer_whos.endpoints.get_available_sites",
            ),
            UrlMap(
                name="get-hydroserver-info",
                url="get-hydroserver-info/",
                controller="water_data_explorer_whos.endpoints.get_hydroserver_info",
            ),
            UrlMap(
                name="available-variables",
                url="available-variables/",
                controller="water_data_explorer_whos.groups.available_variables",
            ),
            UrlMap(
                name="available-regions",
                url="available-regions/",
                controller="water_data_explorer_whos.groups.available_regions",
            ),
            UrlMap(
                name="catalog-filter",
                url="catalog-filter/",
                controller="water_data_explorer_whos.groups.catalog_filter",
            ),
            UrlMap(
                name="get-variables-for-country",
                url="get-variables-for-country/",
                controller="water_data_explorer_whos.groups.get_variables_for_country",
            ),
            UrlMap(
                name="get-download-hs",
                url="get-download-hs/",
                controller="water_data_explorer_whos.endpoints.get_download_hs",
            ),
        )

        return url_maps

    def permissions(self):
        """
        Example permissions method.
        """
        # Viewer Permissions
        delete_hydrogroups = Permission(
            name="delete_hydrogroups",
            description="Delete a Hydrogroup from the App",
        )

        block_map = Permission(
            name="block_map",
            description="locks the map to a certain limit",
        )

        admin = PermissionGroup(
            name="admin", permissions=(delete_hydrogroups, block_map)
        )

        permissions = (admin,)

        return permissions

    def custom_settings(self):
        custom_settings = (
            CustomSetting(
                name="Views Names",
                type=CustomSetting.TYPE_STRING,
                description="Name of the region holding the views (e.g. La Plata Basin)",
                required=False,
            ),
            CustomSetting(
                name="InstitutionLogo",
                type=CustomSetting.TYPE_STRING,
                description="Link containing the isntitution logo.",
                required=False,
            ),
            CustomSetting(
                name="Boundary Geoserver Endpoint",
                type=CustomSetting.TYPE_STRING,
                description='Geoserver endpoint for the hydroshare resource containning the layer (e.g:"https://geoserver.hydroshare.org/geoserver/layerID")',
                required=False,
            ),
            CustomSetting(
                name="Boundary Workspace Name",
                type=CustomSetting.TYPE_STRING,
                description="workspace and layer name (e.g workspace:layername)",
                required=False,
            ),
            CustomSetting(
                name="Boundary Layer Name",
                type=CustomSetting.TYPE_STRING,
                description="layer name (e.g workspace:layername)",
                required=False,
            ),
            CustomSetting(
                name="Boundary Movement",
                type=CustomSetting.TYPE_BOOLEAN,
                description="Block or Allow movement outside the map boundary layer (True/False)",
                required=False,
            ),
            CustomSetting(
                name="Boundary Color",
                type=CustomSetting.TYPE_STRING,
                description="The color style for the boundary (e.g #ffcc33)",
                required=False,
            ),
            CustomSetting(
                name="Boundary Width",
                type=CustomSetting.TYPE_STRING,
                description="Width of the boundary. A number from 1 to 10",
                required=False,
            ),
        )
        return custom_settings

    #### Persistant storage ###
    def persistent_store_settings(self):
        ps_settings = (
            PersistentStoreDatabaseSetting(
                name="catalog_db",
                description="catalogs database",
                initializer="water_data_explorer_whos.init_stores.init_catalog_db",
                required=True,
            ),
        )
        return ps_settings
