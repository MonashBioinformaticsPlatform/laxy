<template>
  <div>
    <md-layout md-gutter>
      <md-layout md-flex="100" md-column>
        <h3>{{ titleText }}</h3>
        <form novalidate @submit.stop.prevent="handleSubmit">
          <md-input-container>
            <label>{{ labelText }}</label>
            <md-textarea v-model="csv_text" rows="3" :placeholder="placeholderText"></md-textarea>
          </md-input-container>
          <!-- Add a button or other actions if needed -->
          <!-- <md-button class="md-primary md-raised" @click="processData">Process Data</md-button> -->
        </form>
      </md-layout>
    </md-layout>
  </div>
</template>

<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";
import { Prop, Watch } from "vue-property-decorator";

@Component({
  components: {},
})
export default class CsvTextForm extends Vue {
  @Prop({ default: "" })
  public initialText: string;

  @Prop({ default: "Paste CSV or TSV data" })
  public titleText: string;

  @Prop({ default: "Paste your CSV or TSV data here" })
  public labelText: string;

  @Prop({ default: "sample_id,barcode\nsample1,TACGAGTACAGACA" })
  public placeholderText: string;

  @Prop({ default: null })
  public showColumns: string[] | null;

  public csv_text: string = "";

  created() {
    if (this.initialText) {
      this.csv_text = this.initialText;
      // Optionally parse and emit on creation if initial text exists
      // this.emitParsedData(this.csv_text); 
    }
  }

  handleSubmit() {
    this.emitParsedData(this.csv_text);
  }

  @Watch("csv_text")
  onCsvTextChanged(newVal: string, oldVal: string) {
    this.emitParsedData(newVal);
  }

  processData() {
    this.emitParsedData(this.csv_text);
  }

  parseText(text: string): Record<string, string>[] {
    const trimmedText = text.trim();
    if (!trimmedText) {
      return [];
    }

    const isTSV = this.detectTSV(trimmedText);
    const delimiter = isTSV ? '\t' : ',';

    const lines = trimmedText.split('\n').filter(line => line.trim() !== '');

    if (lines.length < 1) { // Needs at least a header row
      return [];
    }

    const headers = lines[0].split(delimiter).map(header => header.trim());
    const dataRows = lines.slice(1);

    return dataRows.map(line => {
      const values = line.split(delimiter).map(field => field.trim());
      let rowObject: Record<string, string> = {};
      headers.forEach((header, index) => {
        rowObject[header] = values[index] || ''; // Handle potential missing values for a header
      });

      if (this.showColumns && this.showColumns.length > 0) {
        const filteredRowObject: Record<string, string> = {};
        this.showColumns.forEach(columnName => {
          if (rowObject.hasOwnProperty(columnName)) {
            filteredRowObject[columnName] = rowObject[columnName];
          }
        });
        return filteredRowObject;
      }

      return rowObject;
    });
  }

  emitParsedData(text: string): void {
    const parsedData = this.parseText(text);
    //console.dir(parsedData);
    this.$emit("data-modified", parsedData);
  }

  detectTSV(text: string): boolean {
    if (!text) {
      return false;
    }
    const firstLine = text.split('\n')[0];
    if (!firstLine) {
      return false;
    }
    const tabCount = (firstLine.match(/\t/g) || []).length;
    return tabCount > 1; // Checks for more than one tab
  }
}
</script>

<style scoped>
/* Add any component-specific styles here if needed */
.md-input-container {
  margin-bottom: 16px;
}
</style>
