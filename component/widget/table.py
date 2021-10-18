from traitlets import List, Unicode
import ipyvuetify as v


__all__ = ["VueDataFrame"]


class VueDataFrame(v.VuetifyTemplate):
    """
    Vuetify DataTable rendering of a pandas DataFrame

    Args:
        data (DataFrame) - the data to render
        title (str) - optional title
    """

    from pandas import DataFrame

    headers = List([]).tag(sync=True, allow_null=True)
    items = List([]).tag(sync=True, allow_null=True)
    search = Unicode("").tag(sync=True)
    title = Unicode("DataFrame").tag(sync=True)
    index_col = Unicode("").tag(sync=True)
    template = Unicode(
        """
        <template>
          <v-card>
            <v-card-title>
              <span class="title font-weight-bold">{{ title }}</span>
              <v-spacer></v-spacer>
                <v-text-field
                    v-model="search"
                    append-icon="mdi-magnify"
                    label="Search ..."
                    single-line
                    hide-details
                ></v-text-field>
            </v-card-title>
            <v-data-table
                :headers="headers"
                :items="items"
                :search="search"
                :item-key="index_col"
                :footer-props="{'items-per-page-options': [5, 20, 40]}"
            >
                <template v-slot:no-data>
                  <v-alert :value="true" color="error" icon="mdi-alert">
                    Sorry, nothing to display here :(
                  </v-alert>
                </template>
                <template v-slot:no-results>
                    <v-alert :value="true" color="error" icon="mdi-alert">
                      Your search for "{{ search }}" found no results.
                    </v-alert>
                </template>
                <template v-slot:items="rows">
                  <td v-for="(element, label, index) in rows.item"
                      @click=cell_click(element)
                      >
                    {{ element }}
                  </td>
                </template>
            </v-data-table>
          </v-card>
        </template>
        """
    ).tag(sync=True)

    def __init__(self, *args, data=DataFrame(), title=None, **kwargs):
        super().__init__(*args, **kwargs)

        from json import loads

        data = data.reset_index()
        self.index_col = data.columns[0]
        headers = [{"text": col, "value": col} for col in data.columns]
        headers[0].update({"align": "left", "sortable": True})
        self.headers = headers
        self.items = loads(data.to_json(orient="records"))
        if title is not None:
            self.title = title
