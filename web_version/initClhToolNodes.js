import { api } from "/scripts/api.js";
import { app } from "/scripts/app.js";
import { RenderAllUeLinks } from "./use_links_ui.js";
import { chartGraphWidget,addChartWidget,updateChartOption } from "./echart/extras_node_widgets.js";
import { codeMirrorWidget,addCodeMirrorWidget,exeCodeMirror } from "./codemirror/extras_node_widgets.js";
import {javascript} from "/extensions/ComfyUi-clh-Tool/extensions/core/node_modules/@codemirror/lang-javascript/dist/index.js"
import { EditorView, basicSetup } from "/extensions/ComfyUi-clh-Tool/extensions/core/node_modules/codemirror/dist/index.js";
//import { javascript } from "@codemirror/lang-javascript";

app.registerExtension({
    name:"clhTool-extension",

    init() {

    },
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if(!nodeData?.category?.includes("_clh") || !nodeData?.name?.endsWith("_clh")) {
			// console.log("bx-extension，beforeRegisterNodeDef",nodeData.category)
			return;
		}
		switch (nodeData.name) {

			case "MathExpression_clh":
				const refreshMathExpressionInput = (thisNode,targetSlot)=>{
					
					var length = thisNode.inputs.length
					//减节点
					if(length - 2  <= 0 ){
						// 小于一个节点了
						// break;
					}else  if (thisNode.inputs[length-1].link == null && thisNode.inputs[length-2].link == null) {
						setTimeout(function() {
							thisNode.removeInput(length-1);
							console.log("减节点！",length-1);
							thisNode.computeSize([0,40])
						}, 10);
					} else {
						//不符合变动条件什么都不做
						// break;
					}
					
				}
			    const onGetMaskSizeConnectInput = nodeType.prototype.onConnectInput;
                nodeType.prototype.onConnectInput = function (targetSlot, type, output, originNode, originSlot) {
                    const v = onGetMaskSizeConnectInput? onGetMaskSizeConnectInput.apply(this, arguments): undefined
                    if (1 === this.inputs.length) {
                        return; // already set, do nothing
                    }
					const thisNode = this;
					const _inputs_type = "*";
					var length = thisNode.inputs.length
					//加节点
					if (thisNode.inputs[length-1].link || length-1 == targetSlot) {
						thisNode.addInput(`param${length}`, _inputs_type);
						console.log("加节点！",length)
						
						thisNode.computeSize([0,40])
						//添加节点后无需减节点，结束返回
						return;
					}
					// 尝试减节点
					refreshMathExpressionInput(this,targetSlot)
                    return v;
                }
				const onMathExpressionDisconnectInput = nodeType.prototype.disconnectInput;
                nodeType.prototype.disconnectInput = function (targetSlot, type, output, originNode, originSlot) {
                    const v = onMathExpressionDisconnectInput? onMathExpressionDisconnectInput.apply(this, arguments): undefined
                    if (1 === this.inputs.length) {
						return; // already set, do nothing
					}

					refreshMathExpressionInput(this,targetSlot)
					

					return v;
                }
//				记录默认事件动作
				const MathExpression_DebugExecuted = nodeType.prototype.onExecuted;
				nodeType.prototype.onExecuted = function(result) {
//				    执行默认事件动作
					const r = MathExpression_DebugExecuted? MathExpression_DebugExecuted.apply(this,arguments): undefined
					let values = result["value"].toString().split('x');
					const result_to_label = this.widgets.find(w => w.name === "result_to_label")["value"];
					if(result_to_label){
						this.title = result_to_label + values;
					}
					return r
				}
				break;

			case "JoinStringMulti_clh":
				const JoinStringMultiCreated = nodeType.prototype.onNodeCreated || function() {};
				
				nodeType.prototype.onNodeCreated = function () {
					JoinStringMultiCreated.apply(this, arguments);
					
					this.inputs_offset = nodeData.name.includes("selective") ? 1 : 0;
                    //添加小组件（组件类型，组件名，组件）
					this.addWidget("button", "Update inputs", null, () => {
						refreshJoinStringMultiInput(this);
					});

				}
				//刷新输入参数的方法
				const refreshJoinStringMultiInput = (thisNode) => {
					if (!thisNode.inputs) {
						thisNode.inputs = [];
					}
					
					const input_type = "STRING";
					const target_number_of_inputs = thisNode.widgets.find(w => w.name === "inputcount")["value"];
					const value_of_inputs = thisNode.inputs.filter(w => w.name .startsWith("string_"));
				
					if (target_number_of_inputs === thisNode.inputs.length) {
						// already set, do nothing
					}else
					if (target_number_of_inputs < value_of_inputs.length) {
						for (let i = thisNode.inputs.length; i >= thisNode.inputs_offset + target_number_of_inputs; i--)
							setTimeout(function() {thisNode.removeInput(i);}, 10);
							
					} else {
						for (let i = thisNode.inputs.length + 1 - thisNode.inputs_offset; i <= target_number_of_inputs; ++i)
							thisNode.addInput(`string_${i}`, input_type);
					}
				}
				const onPreviewAnimationConnectInput = nodeType.prototype.onConnectInput;
                nodeType.prototype.onConnectInput= function (targetSlot, type, output, originNode, originSlot) {
                    const v = onPreviewAnimationConnectInput? onPreviewAnimationConnectInput.apply(this, arguments): undefined
                    refreshJoinStringMultiInput(this);
                    return v;
                }
				const onJoinStringMultiDisconnectInput = nodeType.prototype.disconnectInput;
                nodeType.prototype.disconnectInput = function (targetSlot, type, output, originNode, originSlot) {
                    const v = onJoinStringMultiDisconnectInput? onJoinStringMultiDisconnectInput.apply(this, arguments): undefined
                    refreshJoinStringMultiInput(this);
                    return v;
                }
				break;

			case "String2ImgFatLabels_clh":
				const String2ImgFatLabelsCreated = nodeType.prototype.onNodeCreated || function() {};

				nodeType.prototype.onNodeCreated = function () {
					String2ImgFatLabelsCreated.apply(this, arguments);

					this.inputs_offset = nodeData.name.includes("selective") ? 1 : 0;
                    //添加小组件（组件类型，组件名，组件）
//					this.addWidget("image", "select Font Path", null, (value) => {
//					    const font_path_widgets = this.widgets.find(w => w.name === "font_path");
//                        font_path_widgets.value = value
//
//					});

				}
				break;
			case "String2Image_clh":
				const String2FatLabelsCreated = nodeType.prototype.onNodeCreated || function() {};

				nodeType.prototype.onNodeCreated = function () {
					String2FatLabelsCreated.apply(this, arguments);

					this.inputs_offset = nodeData.name.includes("selective") ? 1 : 0;
                    //添加小组件（组件类型，组件名，组件）
//					this.addWidget("button", "select Font Path", null, (value) => {
//					    const font_path_widgets = this.widgets.find(w => w.name === "font_path");
//                        font_path_widgets.value = value
//
//					});

				}
				break;
			case "EchartGraph_clh":
				const EchartGraphCreated = nodeType.prototype.onNodeCreated || function() {};

				nodeType.prototype.onNodeCreated = function () {
					EchartGraphCreated.apply(this, arguments);
					this.inputs_offset = nodeData.name.includes("selective") ? 1 : 0;
                    //添加小组件（组件类型，组件名，组件）
//					this.addCustomWidget(chartGraphWidget(this, "clhTool_chart", true));
                    addChartWidget(this,"clhTool_chart",{  },app)
				}

//				记录默认事件动作
				const EchartGraph_clh_OnExecuted = nodeType.prototype.onExecuted;
				nodeType.prototype.onExecuted = function(result) {
//				    执行默认事件动作
					const r = EchartGraph_clh_OnExecuted? EchartGraph_clh_OnExecuted.apply(this,arguments): undefined
					this.chartOptions = result
					updateChartOption(this,result);

					return r
				}
				break;
			case "JavaScript_clh":
				const JavaScriptCreated = nodeType.prototype.onNodeCreated || function() {};
				nodeType.prototype.onNodeCreated = function () {
					JavaScriptCreated.apply(this, arguments);
                    //初始化参数组件
//                    const value_of_inputs = this.inputs.filter(w => w.name == "param");
                    const node = this;
//                    value_of_inputs[0].widget.serializeValue =  () => {
//                        var link = app.graph.links.filter(link =>link.id == value_of_inputs[0].link)[0];
//                        var a = node
//                        return [[link.id, link.origin_slot],]
//                    };
				}

//				记录默认事件动作
				const JavaScript_clh_OnExecuted = nodeType.prototype.onExecuted;
				nodeType.prototype.onExecuted = function(result) {
//				    执行默认事件动作
					const r = JavaScript_clh_OnExecuted ? JavaScript_clh_OnExecuted.apply(this,arguments): result
//					exeCodeMirror(this, result);

					return r
				}
                // Node Created
//                const onNodeCreatedJavaScript = nodeType.prototype.onNodeCreated;
//                nodeType.prototype.onNodeCreated = function () {
//                    const ret = onNodeCreatedJavaScript? onNodeCreatedJavaScript.apply(this, arguments) : undefined;
//                    addCodeMirrorWidget(this,"clhTool_codemirror",{  },app)
//                    return ret;
//                };
				break;
		}

	},
    async setup(){
        /*
        When we draw connections, do the ue ones as well (logic for on/off is in lrc)
        */
        const drawConnections = LGraphCanvas.prototype.drawConnections;
        LGraphCanvas.prototype.drawConnections = function(ctx) {
            drawConnections?.apply(this, arguments);
            RenderAllUeLinks.render_all_ue_links(ctx);
        }
        api.addEventListener("status", ({detail}) => {
            RenderAllUeLinks.note_queue_size(detail ? detail.exec_info.queue_remaining : 0)
        });
        console.log("注册clhTool扩展！")
    },
    async getCustomWidgets() {
        return {
            CLHCODE(node, inputName, inputData) {

                const defaultVal = inputData[1].default || "";
                return addCodeMirrorWidget(node, inputName, { defaultVal, ...inputData[1] }, app);

            }
        }
    }
})

api.addEventListener("execution_start", (node , prompt_id, output)=>{
    console.log(node,prompt_id,output);
});
