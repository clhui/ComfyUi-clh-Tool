/*
 * Title: Extras widgets
 * Author: AlekPet
 * Github: https://github.com/AlekPet/ComfyUI_Custom_Nodes_AlekPet/tree/master/ExtrasNode
 */

import {
	app
} from "../../../scripts/app.js";
import {
	$el
} from "../../../scripts/ui.js";
//import { rgbToHex, isValidStyle } from "../../utils.js";
//import { RecognationSpeechDialog } from "./extras_node_dialogs.js";
import  "./echarts.min.js"
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

function getVoiceAndSettings() {
	const voices = speechSynthesis.getVoices();

	const {
		voice,
		volume,
		pitch,
		rate
	} =
	RecognationSpeechDialog.getSettingsRecSpeechLS();
	const voiceSelected = voices.filter((v) => v.name === voice);

	return {
		voice: voiceSelected.length ? voiceSelected[0] : null,
		volume,
		pitch,
		rate,
	};
}


function chartGraphWidget(node, inputName, inputData) {
	const widgetType = "clhTool_chart_graph"
	const widget = {
		type: widgetType,
		name: inputName,
		value: inputData,
		size: ['100%', '100'],
		options: {
//			hideOnZoom: true
		},
//		text_element: widgetsText?.inputEl,
		draw(ctx, node, widget_width, y, widget_height) {
			const hidden = false // widgetsText?.element?.hidden;

			widget.element.dataset.shouldHide = hidden ? "true" : "false";
			const isInVisibleNodes =
				widget.element.dataset.isInVisibleNodes === "true";
			const isCollapsed = widget.element.dataset.collapsed === "true";
			const actualHidden = hidden || !isInVisibleNodes || isCollapsed;
			const wasHidden = widget.element.hidden;
//			widget.element.hidden = actualHidden;
//			widget.element.style.display = actualHidden ? "none" : "flex";
			if (actualHidden && !wasHidden) {
				widget.options.onHide?.(widget);
			}

			if (hidden) {
				return;
			}

			Object.assign(
				widget.element.style,
				getPostition(ctx, widget_width, y, node.size[1])
			);
		},
		computeSize(...args) {
			return ['100%', '100'];
		},
		callback(v) {

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


		buttons.push(
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

	}

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
		[...buttons	]
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
    initChart("chartGraphWidget" + node._id)
	return widget;
}

function addChartWidget(node, name, opts, app) {
  const inputEl = document.createElement('div')
//  inputEl.className = 'comfy-multiline-input'
  inputEl.value = opts.defaultVal
  inputEl.placeholder = opts.placeholder || name
  inputEl.style = 'height:100px;background-color: var(--comfy-input-bg);'
  inputEl.style = 'height:100px;background-color: #ffffff;'
  if (app.vueAppReady) {
//    inputEl.spellcheck = useSettingStore().get(
//      'Comfy.TextareaWidget.Spellcheck'
//    )
  }

  const widget = node.addDOMWidget(name, 'ChartWidget', inputEl, {
    getValue() {
      return inputEl.value
    },
    setValue(v) {
      inputEl.value = v
    },
    onDraw(widgetNew){
        inputEl.id = ['ChartWidget', widgetNew.options.node.id, widgetNew.y ].join('_')
        myChart.resize();
    },
    node
  })
  widget.inputEl = inputEl

  inputEl.addEventListener('input', () => {
    widget.callback?.(widget.value)
  })
  const myChart = initChart(inputEl);

  widget.myChart = myChart
  return { minWidth: 400, minHeight: 200, widget }
}

function initChart(element){

	// 基于准备好的 DOM，初始化 ECharts 实例
//        var myChart = echarts.init(document.getElementById(divId));
    var myChart = echarts.init(element);

    // 指定图表的配置项和数据
    var option = {
            title: {
                text: 'ECharts 入门示例'
            },
            tooltip: {
                trigger: 'axis'},
            legend: {
                data: ['销量','比例'],
                left: 'center', // 水平居中
                bottom: '5%',
            },
            xAxis: {
                type: 'category',
                data: ["衬衫", "羊毛衫", "雪纺衫", "裤子", "高跟鞋", "袜子"]
            },
            yAxis: [
                {
                    type: 'value',
                    name: '销量',
                    min: 0,
                    position: 'left',
                    axisLine: {
                        lineStyle: {
                            color: '#5793f3'
                        }
                    },
                    axisLabel: {
                        formatter: '{value}件'
                    }
                },
                {
                    type: 'value',
                    name: '比例',
                    position: 'right',
                    axisLine: {
                        lineStyle: {
                            color: '#d14a61'
                        }
                    },
                    axisLabel: {
                        formatter: '{value}°C'
                    }
                }
            ],
            grid: {
                // 网格配置
                splitLine: {
                    // 分割线配置
                    show: true, // 显示分割线
                    lineStyle: {
                        // 分割线样式
                        color: '#f00', // 设置分割线颜色为红色
                        width: 1, // 分割线宽度
                        type: 'solid' // 分割线类型，如实线、虚线等
                    },
                    // 确保 markLine 显示在正确的 y 轴上（这里是 y2 轴）
                    yAxisIndex: 1
                }
                // ... 其他网格配置 ...
            },
            series: [{
                name: '销量',
                type: 'bar',
                data: [5, 20, 36, 10, 10, 20],
                yAxisIndex: 0 // 对应第一个 y 轴
            },{
                name: '比例',
                type: 'line',
                axisLine: {
                    lineStyle: {
                        color: '#d14a61'
                    }
                },
                data: [5, 20, 36, 10, 10, 20],
                // 对应第二个 y 轴
                yAxisIndex: 1 ,
                // 设置线条颜色、宽度等样式
                lineStyle: {
                    color: '#ff0000', // 红色线条
                    width: 2 // 线条宽度
                },
                // 设置数据点的颜色、大小等样式
                itemStyle: {
                    color: '#00ff00' // 绿色数据点
                },
                // 如果需要填充区域，并设置渐变色
                areaStyle: {
                    // 线性渐变，前四个参数分别是 x0, y0, x2, y2, 表示渐变的方向
                    // 如果 x0 等于 x2 且 y0 等于 y2，则渐变为径向渐变
                    // 此处为线性渐变从左到右
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 1,
                    y2: 0,
                    color: {
                        // 数组，表示渐变的颜色，每一项是一个对象
                        // {offset: 渐变的位置（0~1）, color: 对应的颜色}
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 1,
                        y2: 0,
                        colorStops: [{
                            offset: 0, color: 'red' // 0％处的颜色
                        }, {
                            offset: 1, color: 'blue' // 100％处的颜色
                        }],
                        global: false // 缺省为 false
                    }
                }
            },{
                name: '访问来源',
                type: 'pie',
                radius: '50%',  // 设置饼图的半径
                data: [
                    {value: 1048, name: '搜索引擎'},
                    {value: 735, name: '直接访问'},
                    {value: 580, name: '邮件营销'},
                    {value: 484, name: '联盟广告'},
                    {value: 300, name: '视频广告'}
                ],
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        };

        // 使用刚指定的配置项和数据显示图表
    myChart.setOption(option);
//        setInterval(()=>{
//			option.series[0].data = option.series[0].data.map(element => element * 2)
//			option.series[1].data = option.series[1].data.map(element => element + 1 )
//			// 使用刚指定的配置项和数据显示图表
//			myChart.setOption(option);
//		},2000)
    element.myChart = myChart
    return myChart
}
function updateChartOption(node, result){
    const chart_widget = node.widgets.find(w => w.name === "clhTool_chart");
    const chartOptions_widget = node.widgets.find(w => w.name === "chartOptions");
    if(chart_widget){
        if(result.chartOptions){
            chartOptions_widget.value = result.chartOptions

        }
        try {
            var jsonObject = JSON.parse(chartOptions_widget.value);
            // 如果解析成功，继续处理 jsonObject
            if(!chartOptions_widget.cleared){
                chart_widget.myChart.clear()
                chartOptions_widget.cleared = true
            }
            chart_widget.myChart.setOption(jsonObject)
        } catch (e) {
            console.error("Parsing myChart option error:", e);
            // 处理解析错误
        }
    }
}
export {
	chartGraphWidget,
	getPostition,addChartWidget,updateChartOption
};