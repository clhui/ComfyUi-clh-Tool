import { api } from "../../../scripts/api.js";
import { app } from "../../../scripts/app.js";

app.registerExtension({
    name:"bx-extension",

	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if(!nodeData?.category?.endsWith("_clh") || !nodeData?.name?.endsWith("_clh")) {
			// console.log("bx-extension，beforeRegisterNodeDef",nodeData.category)
			return;
		}
		switch (nodeData.name) {

			case "MathExpression_clh":
				const refreshMathExpressionInput = (thisNode,targetSlot)=>{
					
					var length = thisNode.inputs.length
					//减节点
					// for(let i = 0;i < length;i++){
						//只剩一个节点了
						// if(length - 2 - i == 0 ){
							// break;
						// }else  if (thisNode.inputs[length-i-1].link == null && thisNode.inputs[length-i-2].link == null) {
							// setTimeout(function() {thisNode.removeInput(length-1-i);console.log("减节点！",length-1-i)}, 10);
						// } else {
							//不符合变动条件什么都不做
							// break;
						// }
						
					// }
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
				const onVRAM_DebugExecuted = nodeType.prototype.onExecuted;
				nodeType.prototype.onExecuted = function(message) {
//				    执行默认事件动作
					const r = onVRAM_DebugExecuted? onVRAM_DebugExecuted.apply(this,arguments): undefined
					let values = message["value"].toString().split('x');
					const result_to_label = this.widgets.find(w => w.name === "result_to_label")["value"];
					if(result_to_label){
						this.title = result_to_label+ values;
					}
					if (typeof string!== "undefined" && string!== null && string!== "") {
                        console.log("字符串不是空的，也不是 null");
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

		}

	},
    async setup(){
        console.log("注册扩展！")
    }
})