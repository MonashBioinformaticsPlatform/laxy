<template>
    <md-boards :md-controls="true" :md-swipeable="true">
        <md-board id="slide1">
            <vue-markdown>
                <!-- @formatter:off -->
**Example CSV format (Sample name, R1, R2):**

```csv
SampleA,ftp://bla_lane1_R1.fastq.gz,ftp://bla_lane1_R2.fastq.gz
SampleA,ftp://bla_lane2_R1.fastq.gz,ftp://bla_lane2_R2.fastq.gz
SampleB,ftp://bla2_R1_001.fastq.gz,ftp://bla2_R2_001.fastq.gz
       ,ftp://bla2_R1_002.fastq.gz,ftp://bla2_R2_002.fastq.gz
SampleC,ftp://foo2_lane4_1.fastq.gz,ftp://foo2_lane4_2.fastq.gz
SampleC,ftp://foo2_lane5_1.fastq.gz,ftp://foo2_lane5_2.fastq.gz
```
<!-- @formatter:on -->
            </vue-markdown>
        </md-board>
        <md-board id="slide2">
            <vue-markdown>
                <!-- @formatter:off -->
**CSV format details**

* Each row represents a single biological replicate (sample + condition + biological replicate).
* Rows with identical sample names are considered technical replicates and may be merged for analysis.
* For single-end data, omit the R2 file column.
                <!-- @formatter:on -->
            </vue-markdown>
        </md-board>
    </md-boards>
</template>

<script lang="ts">
    import Vue from "vue";
    import Component from "vue-class-component";
    import VueMarkdown from 'vue-markdown';

    @Component({
        components: {'vue-markdown': VueMarkdown},
        filters: {}
    })
    export default class CSVSampleListUploadAboutBox extends Vue {
    }
</script>
