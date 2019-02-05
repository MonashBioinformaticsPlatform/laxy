<template>
<vue-markdown>
    <!-- @formatter:off -->
**Import ENA and SRA public datasets**
```
```
The [European Nucleotide Archive (ENA)](http://www.ebi.ac.uk/ena) at EMBL-EBI provides publicly available datasets from high-throughput sequencing platforms.
```
```
ENA also includes datasets from the [NCBI Sequence Read Archive (SRA)](https://www.ncbi.nlm.nih.gov/sra).
```
```
Search ENA by Project/Study (`SRP&hellip;`/`PRJ&hellip;`), Experiment (`SRX&hellip;`/`ERX&hellip;`), Run (`SRR&hellip;`/`ERR&hellip;`) or
Sample (`SAM&hellip;`/`ERS&hellip;`) accessions.
    <!-- @formatter:on -->
</vue-markdown>
</template>

<script lang="ts">
    import Vue from "vue";
    import Component from "vue-class-component";
    import VueMarkdown from 'vue-markdown';

    @Component({
        components: {'vue-markdown': VueMarkdown},
        filters: {}
    })
    export default class ENASearchAboutBox extends Vue {
    }
</script>
