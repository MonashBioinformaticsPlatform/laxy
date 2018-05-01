#!/usr/bin/env groovy

/*
Download a Groovy config (NextFlow) from SciLifeLab/NGI-RNASeq
and output a JSON version

$ groovy scripts/get_igenomes_json.groovy >laxy_backend/templates/genomes.json
*/

import groovy.json.JsonOutput

/*
public String get_url_content(url) {

    def urlContents = url.toURL().getText()

    return urlContents
}

text = get_url_content("https://raw.githubusercontent.com/SciLifeLab/NGI-RNAseq/master/conf/igenomes.config")
text.eachLine {
    println it
}
*/

// final ConfigObject params = new ConfigSlurper().parse(new File("params.groovy").toURI().toURL());

def params = [params: [igenomes_base:'iGenomes']]
def slurper = new ConfigSlurper()
slurper.setBinding(params)
final ConfigObject config = slurper.parse("https://raw.githubusercontent.com/SciLifeLab/NGI-RNAseq/master/conf/igenomes.config".toURI().toURL())
// println config.toString()

println JsonOutput.prettyPrint(JsonOutput.toJson(config)).stripIndent()
