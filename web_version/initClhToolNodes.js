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
		if(!nodeData?.category?.includes("_clh") && !nodeData?.name?.endsWith("_clh") && !nodeType?.comfyClass?.endsWith("_clh")) {
			// console.log("bx-extension，beforeRegisterNodeDef",nodeData.category)
			return;
		}
		switch (nodeType?.comfyClass) {

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
			
			case "duplicate_checker_clh":
				// 为重复大模型文件检测节点添加帮助功能，基于help_popup.js的实现
				const CLHDuplicateCheckerCreated = nodeType.prototype.onNodeCreated || function() {};
				
				nodeType.prototype.onNodeCreated = function () {
					CLHDuplicateCheckerCreated.apply(this, arguments);
					
					// 初始化帮助功能
					this.show_doc = false;
					this.docCtrl = null;
				}
				
				// 创建文档样式表
				const create_clh_documentation_stylesheet = () => {
					const tag = 'clh-documentation-stylesheet'
					let styleTag = document.head.querySelector('#' + tag)
					
					if (!styleTag) {
						styleTag = document.createElement('style')
						styleTag.type = 'text/css'
						styleTag.id = tag
						styleTag.innerHTML = `
						.clh-documentation-popup {
							background: var(--comfy-menu-bg);
							position: absolute;
							color: var(--fg-color);
							font: 12px monospace;
							line-height: 1.5em;
							padding: 10px;
							border-radius: 10px;
							border-style: solid;
							border-width: medium;
							border-color: var(--border-color);
							z-index: 5;
							overflow: hidden;
							max-width: 500px;
							min-width: 300px;
						}
						.clh-content-wrapper {
							overflow: auto;
							max-height: 400px;
							/* Scrollbar styling for Chrome */
							&::-webkit-scrollbar {
								width: 6px;
							}
							&::-webkit-scrollbar-track {
								background: var(--bg-color);
							}
							&::-webkit-scrollbar-thumb {
								background-color: var(--fg-color);
								border-radius: 6px;
								border: 3px solid var(--bg-color);
							}
							/* Scrollbar styling for Firefox */
							scrollbar-width: thin;
							scrollbar-color: var(--fg-color) var(--bg-color);
						}
						.clh-content-wrapper h3 {
							color: #4a90e2;
							margin-top: 0;
							margin-bottom: 10px;
						}
						.clh-content-wrapper h4 {
							color: var(--fg-color);
							margin-top: 15px;
							margin-bottom: 8px;
						}
						.clh-content-wrapper ul {
							margin: 8px 0;
							padding-left: 20px;
						}
						.clh-content-wrapper li {
							margin: 4px 0;
						}
						.clh-content-wrapper strong {
							color: #4a90e2;
						}
						`
						document.head.appendChild(styleTag)
					}
				}
				
				// 重写绘制前景方法以添加帮助图标
				const drawFg = nodeType.prototype.onDrawForeground
				nodeType.prototype.onDrawForeground = function (ctx) {
					const r = drawFg ? drawFg.apply(this, arguments) : undefined
					if (this.flags.collapsed) return r
					
					const iconSize = 14
					const iconMargin = 4
					// 图标位置
					const x = this.size[0] - iconSize - iconMargin
					
					let docElement = null
					let contentWrapper = null
					
					// 创建弹出窗口
					if (this.show_doc && !document.querySelector('.clh-documentation-popup')) {
						docElement = document.createElement('div')
						contentWrapper = document.createElement('div')
						docElement.appendChild(contentWrapper)
						
						create_clh_documentation_stylesheet()
						contentWrapper.classList.add('clh-content-wrapper')
						docElement.classList.add('clh-documentation-popup')
						
						// 设置帮助内容
						contentWrapper.innerHTML = `
							<h3>重复大模型文件检测 - 使用说明</h3>
							
							<h4>功能介绍：</h4>
							<p>检测指定目录下的重复大模型文件，帮助清理磁盘空间，支持多线程处理和模型文件过滤。</p>
							
							<h4>参数说明：</h4>
							<ul>
								<li><strong>最小文件大小(MB)：</strong>只检测大于此大小的文件，默认100MB</li>
								<li><strong>仅扫描模型文件：</strong>开启后只检测常见的AI模型文件格式</li>
								<li><strong>最大线程数：</strong>并行处理的线程数量，建议设置为CPU核心数</li>
								<li><strong>目录类型：</strong>选择要扫描的目录范围</li>
								<li><strong>自定义目录：</strong>当选择"其他"时，输入要扫描的目录路径</li>
							</ul>
							
							<h4>支持的模型文件格式：</h4>
							<p>.ckpt, .safetensors, .pt, .pth, .bin, .pkl, .h5, .pb, .onnx, .tflite, .engine, .model 等</p>
							
							<h4>输出说明：</h4>
							<ul>
								<li><strong>duplicate_report：</strong>详细的重复文件检测报告</li>
								<li><strong>log_output：</strong>扫描过程的日志信息</li>
							</ul>
							
							<h4>使用建议：</h4>
							<ul>
								<li>首次扫描建议先选择较小的目录范围</li>
								<li>大目录扫描可能需要较长时间，请耐心等待</li>
								<li>删除重复文件前请仔细确认，建议先备份重要文件</li>
							</ul>
						`
						
						// 调整大小手柄
						const resizeHandle = document.createElement('div')
						resizeHandle.style.width = '0'
						resizeHandle.style.height = '0'
						resizeHandle.style.position = 'absolute'
						resizeHandle.style.bottom = '0'
						resizeHandle.style.right = '0'
						resizeHandle.style.cursor = 'se-resize'
						
						const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--border-color').trim()
						resizeHandle.style.borderTop = '10px solid transparent'
						resizeHandle.style.borderLeft = '10px solid transparent'
						resizeHandle.style.borderBottom = `10px solid ${borderColor}`
						resizeHandle.style.borderRight = `10px solid ${borderColor}`
						
						docElement.appendChild(resizeHandle)
						
						let isResizing = false
						let startX, startY, startWidth, startHeight
						
						resizeHandle.addEventListener('mousedown', function (e) {
							e.preventDefault()
							e.stopPropagation()
							isResizing = true
							startX = e.clientX
							startY = e.clientY
							startWidth = parseInt(document.defaultView.getComputedStyle(docElement).width, 10)
							startHeight = parseInt(document.defaultView.getComputedStyle(docElement).height, 10)
						}, { signal: this.docCtrl.signal })
						
						// 关闭按钮
						const closeButton = document.createElement('div')
						closeButton.textContent = '❌'
						closeButton.style.position = 'absolute'
						closeButton.style.top = '0'
						closeButton.style.right = '0'
						closeButton.style.cursor = 'pointer'
						closeButton.style.padding = '5px'
						closeButton.style.color = 'red'
						closeButton.style.fontSize = '12px'
						
						docElement.appendChild(closeButton)
						
						closeButton.addEventListener('mousedown', (e) => {
							e.stopPropagation()
							this.show_doc = !this.show_doc
							if (docElement.parentNode) {
								docElement.parentNode.removeChild(docElement)
							}
							docElement = null
							if (contentWrapper) {
								contentWrapper.remove()
								contentWrapper = null
							}
						}, { signal: this.docCtrl.signal })
						
						document.addEventListener('mousemove', function (e) {
							if (!isResizing) return
							const scale = app.canvas.ds.scale
							const newWidth = startWidth + (e.clientX - startX) / scale
							const newHeight = startHeight + (e.clientY - startY) / scale
							docElement.style.width = `${newWidth}px`
							docElement.style.height = `${newHeight}px`
						}, { signal: this.docCtrl.signal })
						
						document.addEventListener('mouseup', function () {
							isResizing = false
						}, { signal: this.docCtrl.signal })
						
						document.body.appendChild(docElement)
					}
					// 关闭弹出窗口
					else if (!this.show_doc) {
						const existingPopup = document.querySelector('.clh-documentation-popup')
						if (existingPopup && existingPopup.parentNode) {
							existingPopup.parentNode.removeChild(existingPopup)
						}
					}
					
					// 更新弹出窗口位置
					if (this.show_doc) {
						const popup = document.querySelector('.clh-documentation-popup')
						if (popup) {
							const rect = ctx.canvas.getBoundingClientRect()
							const scaleX = rect.width / ctx.canvas.width
							const scaleY = rect.height / ctx.canvas.height
							
							const transform = new DOMMatrix()
								.scaleSelf(scaleX, scaleY)
								.multiplySelf(ctx.getTransform())
								.translateSelf(this.size[0] * scaleX * Math.max(1.0, window.devicePixelRatio), 0)
								.translateSelf(10, -32)
							
							const scale = new DOMMatrix()
								.scaleSelf(transform.a, transform.d)
							const bcr = app.canvas.canvas.getBoundingClientRect()
							
							const styleObject = {
								transformOrigin: '0 0',
								transform: scale,
								left: `${transform.a + bcr.x + transform.e}px`,
								top: `${transform.d + bcr.y + transform.f}px`,
							}
							Object.assign(popup.style, styleObject)
						}
					}
					
					// 绘制帮助图标
					ctx.save()
					ctx.translate(x - 2, iconSize - 34)
					ctx.scale(iconSize / 32, iconSize / 32)
					ctx.strokeStyle = 'rgba(255,255,255,0.3)'
					ctx.lineCap = 'round'
					ctx.lineJoin = 'round'
					ctx.lineWidth = 2.4
					ctx.font = 'bold 36px monospace'
					ctx.fillStyle = 'orange'
					ctx.fillText('?', 0, 24)
					ctx.restore()
					return r
				}
				
				// 处理鼠标点击事件
				const mouseDown = nodeType.prototype.onMouseDown
				nodeType.prototype.onMouseDown = function (e, localPos, canvas) {
					const r = mouseDown ? mouseDown.apply(this, arguments) : undefined
					const iconSize = 14
					const iconMargin = 4
					const iconX = this.size[0] - iconSize - iconMargin
					const iconY = iconSize - 34
					
					if (
						localPos[0] > iconX &&
						localPos[0] < iconX + iconSize &&
						localPos[1] > iconY &&
						localPos[1] < iconY + iconSize
					) {
						if (this.show_doc === undefined) {
							this.show_doc = true
						} else {
							this.show_doc = !this.show_doc
						}
						if (this.show_doc) {
							this.docCtrl = new AbortController()
						} else {
							if (this.docCtrl) {
								this.docCtrl.abort()
							}
						}
						return true
					}
					return r
				}
				
				// 节点删除时清理
				const onRem = nodeType.prototype.onRemoved
				nodeType.prototype.onRemoved = function () {
					const r = onRem ? onRem.apply(this, []) : undefined
					
					const docElement = document.querySelector('.clh-documentation-popup')
					if (docElement) {
						docElement.remove()
					}
					
					return r
				}
				
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
