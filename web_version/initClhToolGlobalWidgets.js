import { api } from "/scripts/api.js";
import { app } from "/scripts/app.js";

import {
  translateBtnWidget,getPostition
} from "./extras_node_widgets.js";
// Recognation & speech
//const SpeechAndRecognationSpeechLS = localStorage.getItem(
//  `Comfy.Settings.${idExt}.SpeechAndRecognationSpeech`
//);
// Speech & Recognition widget settings
const SpeechAndRecognationSpeech = app.ui.settings.getSettingValue("clhTool.translateBtn.switch")
//? app.ui.settings.getSettingValue("clhTool.translateBtn")
//: true
app.registerExtension({
    name:"clhToolGlobalWidgets-extension",

    init() {

    },
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if(!nodeData?.category?.endsWith("_clh") || !nodeData?.name?.endsWith("_clh")) {
			// console.log("bx-extension，beforeRegisterNodeDef",nodeData.category)
//			return;
		}
        // -- Speech & Recognition speech widget
        // If ui settings is true and SpeechSynthesis or speechRecognition is not undefined
        if (SpeechAndRecognationSpeech ) {
          let nodeIsMultiString = false;
          let outputNode = false;

          if (nodeData?.input && nodeData?.input?.required) {
            for (const inp of Object.keys(nodeData.input.required)) {
              if (nodeData.input.required[inp][1]?.multiline || nodeData.name.toLocaleLowerCase().includes("showtext")) {
                const type = nodeData.input.required[inp][0];

                if (["STRING"].includes(type)) {
                  nodeIsMultiString = true;
                  break;
                }
              }
            }
          }


          if (nodeIsMultiString) {
            // Node Created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
              const ret = onNodeCreated
                            ? onNodeCreated.apply(this, arguments)
                            : undefined;

              // Find all widget type customtext
              const widgetsTextMulti = this?.widgets?.filter((w) =>
                !outputNode
                  ? ["customtext", "converted-widget"].includes(w.type)
                  : ["customtext"].includes(w.type)
              );
              const isIncludesSpeech = this?.widgets?.some(
                (w) => w.type === "clhTool_translation_type"
              );

//              await new Promise((res) =>
//                setTimeout(() => {
//                  res();
//                }, 16 * this.widgets.length)
//              );

              if (!isIncludesSpeech && widgetsTextMulti?.length) {
                widgetsTextMulti.forEach(async (textWidget) => {

				  //添加全自定义节点 constructor
                  this.addCustomWidget(translateBtnWidget(this, "clhTool_translation_button", true, textWidget)                  );
                });
              }
//              nodeType.prototype.addInput();
//    The user requested rich
//    The user requested rich>=13.7.0
//    inference-cli 0.13.0 depends on rich<=13.5.2

              return ret;
            };

            // onConfigure
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = async function (w) {
              onConfigure?.apply(this, arguments);
              if (w?.widgets_values?.length) {
                await new Promise((res) =>
                  setTimeout(() => {
                    res();
                  }, 16 * this.widgets.length)
                );

                const ids_speech_clear = this.widgets.reduce(function (arr,el,idx) {
                      if (el.type === "speak_and_recognation_type") arr.push(idx);
                      return arr;
                    },
                []);

                for (const id of ids_speech_clear)
                  this?.widgets[id]?.callback(w.widgets_values[id]);
              }
            };
          }
        }
        // -- end - Speech & Recognition speech widget


	},
    async setup(){
        console.log("注册clhTool扩展！")
    }
})