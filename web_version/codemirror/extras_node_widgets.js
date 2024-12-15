/*
 * Title: Extras widgets
 * Author: AlekPet
 * Github: https://github.com/AlekPet/ComfyUI_Custom_Nodes_AlekPet/tree/master/ExtrasNode
 */

import {app} from "/scripts/app.js";
import {$el} from "/scripts/ui.js";
import {javascript} from "/extensions/ComfyUi-clh-Tool/extensions/core/node_modules/@codemirror/lang-javascript/dist/index.js"
import { EditorView, basicSetup } from "/extensions/ComfyUi-clh-Tool/extensions/core/node_modules/codemirror/dist/index.js";
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
		top: `${(y) * scale.d + scale.f + rect.top}px`,
		maxWidth: `${w_width - MARGIN * 2}px`,
		maxHeight: `${n_height - MARGIN * 2}px`,
		zIndex: 20,
	};
}



function codeMirrorWidget(node, inputName, inputData) {
	const widgetType = "clhTool_codemirror"
	const widget = {
		type: widgetType,
		name: inputName,
		value: inputData,
		size: ['100%', '100'],
		options: {
			hideOnZoom: true
		},
//		text_element: widgetsText?.inputEl,
		draw(ctx, node, widget_width, y, widget_height) {
//		    inputEl.id = ['CodeMirrorWidget', widgetNew.options.node.id, widgetNew.y ].join('_')
		},
//		computeSize(...args) {
//			return ['100%', '100'];
//		},
		callback(v) {
			widget.value = v ?? inputData;
		},
		onRemove() {
			widget.element?.remove();
		},
	};

	const divs = [];

	//可以生成组件
    divs.push(
        $el("div", {
            id: "chartGraphWidget" + node._id,

            textContent: "To CHN",
            title: "翻译成中文,可前往comfyui设置中 clhTool.translateBtn开启或者关闭",
            style: {
                "font-size": "7px",
                "width": "100%",
                "height": "100px",
                "padding": "1px",
                "height": "12px",
                "line-height": "4px",
                "margin": "2px"
            }
        })
    );



	widget.element = $el(
		"div", {
//			hidden: true,
			style: {
				"display": "flex",
				"margin": "0px",
				"padding": "0px",
				"position": "absolute",
				"text-align": "center",
				"cursor": "pointer",
				"font-size": "1rem",
				"justify-content": "center",
				"align-items": "flex-end",
				"flex-flow": "column",
				"width": "100%",
				"font-family": "monospace",
			}
		},
		[...divs]
	);
	//  节点崩溃时
	const collapse = node.collapse;
	node.collapse = function() {
		collapse.apply(this, arguments);
		if (this.flags?.collapsed) {
			widget.element.hidden = true;
			widget.element.style.display = "none";
		}
		widget.element.dataset.collapsed = this.flags?.collapsed ? "true" : "false";
	};
	//节点删除时
	const onRemovedOrig = node.onRemoved;
	node.onRemoved = function() {
		node?.widgets?.forEach((w) => {
			if (w.type === widgetType) {
				w?.onRemove();
			}
		});
		onRemovedOrig?.apply(node, arguments);
	};

	document.body.appendChild(widget.element);
	return widget;
}

function addCodeMirrorWidget(node, name, opts, app) {
    const inputEl = document.createElement('div')
    //  inputEl.className = 'comfy-multiline-input'
    inputEl.value = opts.defaultVal
    inputEl.placeholder = opts.placeholder || name
//    inputEl.style = 'height:100px;background-color: var(--comfy-input-bg);'
    inputEl.style = 'height:100px; background-color: #ffffff;color:#000000;overflow: auto;border: 1px solid #ddd'

    // 为 div 元素添加 keydown 事件监听器
    inputEl.addEventListener('keydown', function(event) {

          // 阻止事件冒泡到父级元素
          event.stopPropagation();
        // 检查是否是 backspace 键
        if (event.key === 'Backspace') {
          // 可选：阻止浏览器的默认行为（例如，在可编辑内容中阻止删除）
          // event.preventDefault();
          // 如果你还想阻止其他按键，可以在这里添加更多条件
        }
    });

    const widget = node.addDOMWidget(name, 'CodeMirrorWidget', inputEl, {
        getValue() {
            return {inputValue :[myCodeMirror.state.doc.toString(),widget.exeCodeResult ]}
        },
        setValue(v) {
            var value = v
            try{
                value = v.inputValue[0]
            }catch{
                console.log("CodeMirror设置值：",v)
            }
            myCodeMirror.dispatch({
                changes: { from: 0, to: myCodeMirror.state.doc.length, insert: value }
            });
        },
		size: ['100%', '100'],
        onDraw(widgetNew){
            inputEl.id = ['CodeMirrorWidget', widgetNew.options.node.id, widgetNew.y ].join('_')
//            myCodeMirror.resize();
        },
        node
    })
    widget.beforeQueued = () => {
        widget.exeCodeResult = exeCodeMirror(node)
    };
//    widget.serializeValue =  () => {
//        widget.exeResult = exeCodeMirror(node)
//        return [myCodeMirror.state.doc.toString(),widget.exeCodeResult ]
//    };
    widget.inputEl = inputEl

    inputEl.addEventListener('input', () => {
        widget.callback?.(widget.value)
    })
    const myCodeMirror = initCodeMirror(inputEl);

    widget.myCodeMirror = myCodeMirror
    node.myCodeMirror = myCodeMirror
    return widget
}

function initCodeMirror(element){

	// 基于准备好的 DOM，初始化 ECodeMirrors 实例
//        var myCodeMirror = echarts.init(document.getElementById(divId));
//    var myCodeMirror = echarts.init(element);
    var myCodeMirror =  new EditorView({
        doc: 'console.log("Hello world"); \n return "{}";',
        extensions: [
            basicSetup,
            javascript(),
        ],
        parent: element
    });
    element.myCodeMirror = myCodeMirror
    return myCodeMirror
}
function exeCodeMirror(node, result){
	const value_of_inputs = node.widgets.filter(w => w.name == "param");

    var param =  value_of_inputs[0].value
    var myCodeMirror =  node.myCodeMirror
    const codeString =  myCodeMirror.state.doc.toString();
    if(myCodeMirror){
        if(codeString){
            try {
                const func = new Function( "param", "" + codeString + "");
                var resultString = func(param); // 输出: Hello, world!
                node.setOutputData(0,resultString)
                return resultString;
            } catch (e) {
                console.error("Parsing myCodeMirror option error:", e);
                // 处理解析错误
            }
        }
    }
}
export {
	codeMirrorWidget,addCodeMirrorWidget,
	getPostition,exeCodeMirror
};