/*
 * Title: Extras widgets
 * Author: AlekPet
 * Github: https://github.com/AlekPet/ComfyUI_Custom_Nodes_AlekPet/tree/master/ExtrasNode
 */

import { app } from "../../../scripts/app.js";
import { $el } from "../../../scripts/ui.js";
//import { rgbToHex, isValidStyle } from "../../utils.js";
//import { RecognationSpeechDialog } from "./extras_node_dialogs.js";

const CONVERTED_TYPE = "converted-widget";

let translating = false;


// Get position speech SpeechRecognition widget
function getPostition(ctx, w_width, y, n_height, wInput) {
  const MARGIN = 10;

  const rect = ctx.canvas.getBoundingClientRect();
  const transform = new DOMMatrix()
    .scaleSelf(rect.width / ctx.canvas.width, rect.height / ctx.canvas.height)
    .multiplySelf(ctx.getTransform())
    .translateSelf(MARGIN, MARGIN);
  const scale = new DOMMatrix().scaleSelf(transform.a, transform.d);

  return {
    transformOrigin: "0 0",
    transform: scale,
    transform: transform,
    left: `${transform.a * w_width - 165 * scale.a + rect.left}px`,
    top: `${(wInput.last_y - 15) * scale.d + scale.f + rect.top}px`,
    maxWidth: `${w_width - MARGIN * 2}px`,
    maxHeight: `${n_height - MARGIN * 2}px`,
    zIndex: wInput?.inputEl?.style?.zIndex
      ? +wInput?.inputEl.style.zIndex + 1
      : 20,
  };
}

function getVoiceAndSettings() {
  const voices = speechSynthesis.getVoices();

  const { voice, volume, pitch, rate } =
    RecognationSpeechDialog.getSettingsRecSpeechLS();
  const voiceSelected = voices.filter((v) => v.name === voice);

  return {
    voice: voiceSelected.length ? voiceSelected[0] : null,
    volume,
    pitch,
    rate,
  };
}


function translateBtnWidget(node, inputName, inputData, widgetsText) {
  const widget = {
    type: "clhTool_translation_type",
    name: inputName,
    value: inputData,
    size: [42, 1],
    options: { hideOnZoom: true },
    text_element: widgetsText?.inputEl,
    draw(ctx, node, widget_width, y, widget_height) {
      const hidden = widgetsText?.element?.hidden;

      widget.element.dataset.shouldHide = hidden ? "true" : "false";
      const isInVisibleNodes =
        widget.element.dataset.isInVisibleNodes === "true";
      const isCollapsed = widget.element.dataset.collapsed === "true";
      const actualHidden = hidden || !isInVisibleNodes || isCollapsed;
      const wasHidden = widget.element.hidden;
      widget.element.hidden = actualHidden;
      widget.element.style.display = actualHidden ? "none" : "flex";
      if (actualHidden && !wasHidden) {
        widget.options.onHide?.(widget);
      }

      if (hidden) {
        return;
      }

      Object.assign(
        widget.element.style,
        getPostition(ctx, widget_width, y, node.size[1], widgetsText)
      );
    },
    computeSize(...args) {
      return [42, 1];
    },
    callback(v) {
//      if (widgetsText?.element?.hasAttribute("readonly")) return;

      widget.value = v ?? inputData;
      const checkbox = widget.element.querySelector(
        ".alekpet_extras_node_recognition_clear"
      );
      checkbox.checked = widget.value;
    },
    onRemove() {
      widget.element?.remove();
    },
  };

  const buttons = [];

    //可以生成组件
  if (true) {
    function buttonsStyles(
      speechesButtons,
      action = "add",
      className = "alekpet_extras_node_speech_icon_playing"
    ) {
      speechesButtons?.forEach((speechButton) =>
        speechButton?.classList[action](className)
      );

      const settingTestSpeech = document.querySelector(
        ".panel_settings_recognation_speech_voice_test"
      );
      if (settingTestSpeech) {
        if (action === "add") {
          settingTestSpeech.style.opacity = 0.7;
          settingTestSpeech.style.color = "var(--error-text)";
          settingTestSpeech.title = "Cancel test speech";
          settingTestSpeech.textContent = "Cancel test";
        } else {
          settingTestSpeech.style.opacity = 1;
          settingTestSpeech.title = "Run test speech";
          settingTestSpeech.textContent = "Test speech";
          settingTestSpeech.style.color = "limegreen";
        }
      }
    }

    buttons.push(
      $el("button", {
        id: "clhTranslateBtn"+widgetsText.node_id,
        onclick: function () {
          try {
            // Already playing
            if (translating) {
				alert("已开始翻译！");
				return;
            }
            // Start playing text
            const text = widgetsText?.element?.value;
            if (text.trim() !== "") {
				translating = true
				fetch("/clh_translate", {
				  method: "POST",
				  headers: { "Content-Type": "application/json" },
				  body: JSON.stringify({query: text,from:"en",to:"zh" })
				}).then(response => {
				  translating = false;
				  if (!response.ok) {
					  throw new Error("Network response was not ok " + response.statusText);
				  }
				  return response.json();
				}).then(data => {
				    translating = false;
				    // 请求成功，处理响应数据
				    console.log(data);
				    const resultString = data.trans_result.map(person => person.dst).join('\n');
				    widgetsText.element.value = resultString
				}).catch(error => {
				  translating = false;
				  // 处理错误
				  console.error("There was a problem with your fetch operation:", error);
				});
            }
          } catch (err) {
            console.log(err);
          }
        },
        textContent: "To CHN",
        title: "翻译成中文,可前往comfyui设置中 clhTool.translateBtn开启或者关闭",
        style: { "font-size": "7px", "width": "30px","padding": "1px", "height": "12px","line-height": "4px","margin": "2px"}
      })
    );

    buttons.push(
      $el("button", {
        id: "clhTranslateBtn"+widgetsText.node_id,
        onclick: function () {
          try {
            // Already playing
            if (translating) {
				alert("已开始翻译！");
				return;
            }
            // Start playing text
            const text = widgetsText?.element?.value;
            if (text.trim() !== "") {
				translating = true
				fetch("/clh_translate", {
				  method: "POST",
				  headers: { "Content-Type": "application/json" },
				  body: JSON.stringify({query: text,from:"zh",to:"en" })
				}).then(response => {
				  translating = false;
				  if (!response.ok) {
					  throw new Error("Network response was not ok " + response.statusText);
				  }
				  return response.json();
				}).then(data => {
				    translating = false;
				    // 请求成功，处理响应数据
				    console.log(data);
				    widgetsText.element.value = data.trans_result[0].dst
				}).catch(error => {
				  translating = false;
				  // 处理错误
				  console.error("There was a problem with your fetch operation:", error);
				});
            }
          } catch (err) {
            console.log(err);
          }
        },
        textContent: "To Eng",
        title: "翻译成英文，您可以去菜单中clhTool菜单下打开或者关闭此功能",
        style: { "font-size": "7px", "width": "30px","padding": "1px", "height": "12px","line-height": "4px","margin": "2px"}
      })
    );
    buttons.push(
      $el("button", {
        id: "clhTranslateBtn"+widgetsText.node_id,
        onclick: function () {
          try {
            // Already playing
            if (translating) {
				alert("已开始翻译！");
				return;
            }
            // Start playing text
            const text = widgetsText?.element?.value;
            if (text.trim() !== "") {
				translating = true
				fetch("/clh_zhipu", {
				  method: "POST",
				  headers: { "Content-Type": "application/json" },
				  body: JSON.stringify({query: text,from:"zh",to:"en" })
				}).then(response => {
				  translating = false;
				  if (!response.ok) {
					  throw new Error("Network response was not ok " + response.statusText);
				  }
				  return response.json();
				}).then(data => {
				    translating = false;
				    // 请求成功，处理响应数据
				    console.log(data);
				    widgetsText.element.value = data.choices[0].message.content
				}).catch(error => {
				  translating = false;
				  // 处理错误
				  console.error("There was a problem with your fetch operation:", error);
				});
            }
          } catch (err) {
            console.log(err);
          }
        },
        textContent: "智普Ai",
        title: "智普，您可以去菜单中clhTool菜单下打开或者关闭此功能",
        style: { "font-size": "7px", "width": "30px","padding": "1px", "height": "12px","line-height": "4px","margin": "2px"}
      })
    );
  }

  widget.element = $el(
    "div",
    {
        hidden: true,
        style: {
            "display": "none",
			"margin": "0px",
			"padding": "0px",
			"position": "absolute",
			"text-align": "center",
			"cursor": "pointer",
			"font-size": "1rem",
			"justify-content": "center",
			"align-items": "flex-end",
			"flex-flow": "column",
			"width": "60px",
			"font-family": "monospace",
        }
    },
    [
      $el("div",
    {
        style: {
			"position": "relative",
			"display": "flex",
			"gap": "1px",
			"justify-content": "center",
			"align-items": "center",
        }
    }, [...buttons]),
      $el("div", [
        $el("span", {
          textContent: "",
          style: { fontSize: "0.4em" },
        }),
      ]),
    ]
  );
//  节点崩溃时
  const collapse = node.collapse;
  node.collapse = function () {
    collapse.apply(this, arguments);
    if (this.flags?.collapsed) {
      widget.element.hidden = true;
      widget.element.style.display = "none";
    }
    widget.element.dataset.collapsed = this.flags?.collapsed ? "true" : "false";
  };
//节点删除时
  const onRemovedOrig = node.onRemoved;
  node.onRemoved = function () {
    node?.widgets?.forEach((w) => {
      if (w.type === "speak_and_recognation_type") {
        w?.onRemove();
      }
    });
    onRemovedOrig?.apply(node, arguments);
  };

  document.body.appendChild(widget.element);

  return widget;
}
/* ~~~ end - Speech & Recognition speech Widget ~~~ */
function doTranslate(text,from,to){
    fetch("/clh_translate", {
        method: "POST",
        headers: {"Content-Type": "application/json" },
        body: JSON.stringify({query: text,from:"zh",to:"en"})
    }).then(response => {
        translating = false;
        if (!response.ok) {
          throw new Error("Network response was not ok " + response.statusText);
        }
        return response.json();
    }).then(data => {
        translating = false;
        // 请求成功，处理响应数据
        console.log(data);
        widgetsText.element.value = data.trans_result[0].dst
    }).catch(error => {
        translating = false;
        // 处理错误
        console.error("There was a problem with your fetch operation:", error);
    });
}

export {
  translateBtnWidget,
  getPostition
//  makeColorWidget,
//  createPreiviewSize,
//  speechRect,
//  SpeechSynthesis,
//  speakSynthesisUtterance,
};
