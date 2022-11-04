// A Vue Class Component mixin to add copy to clipboard methods

import Vue from 'vue'
import Component from 'vue-class-component'

const Clipboard = require("clipboard");

@Component
export class CopyToClipboard extends Vue {

    async setClipboard(text: string) {
        return new Promise(function (resolve, reject) {
            const tmp_button = document.createElement("button");
            const clipboard = new Clipboard(tmp_button, {
                text: function () {
                    return text;
                },
                action: function () {
                    return "copy";
                },
                container: document.body,
            });
            clipboard.on("success", function (e: Promise<string>) {
                clipboard.destroy();
                resolve(e);
            });
            clipboard.on("error", function (e: Promise<string>) {
                clipboard.destroy();
                reject(e);
            });
            tmp_button.click();
        });
    }

    async setClipboardFlash(
        text: string,
        message: string,
        failMessage: string = "Failed to copy to clipboard :/"
    ) {
        try {
            const displayTime = message.length * 20 + 500;
            await this.setClipboard(text);
            this.$emit("flash-message", { message: message, duration: displayTime });
        } catch (error) {
            const displayTime = failMessage.length * 20 + 1000;
            this.$emit("flash-message", {
                message: failMessage,
                duration: displayTime,
            });
        }
    }
}