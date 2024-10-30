import { app } from "../../../scripts/app.js";

// Adds context menu entries, code partly from pyssssscustom-scripts

function addMenuHandler(nodeType, cb) {
	const getOpts = nodeType.prototype.getExtraMenuOptions;
	nodeType.prototype.getExtraMenuOptions = function () {
		const r = getOpts.apply(this, arguments);
		cb.apply(this, arguments);
		return r;
	};
}

app.registerExtension({
	name: "clhToolContextMenu",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.input && nodeData.input.required) {
		}
	},
    async setup(app) {
        const onChange = (value) => {

        };
        app.ui.settings.addSetting({
            id: "clhTool.translateBtn.switch",
            name: "🟢 Initiates translateBtn of text of Nodes 🔴",
            defaultValue: true,
            type: "boolean",
            options: (value) => [
                { value: true, text: "On", selected: value === true },
                { value: false, text: "Off", selected: value === false },
            ],
        });
        app.ui.settings.addSetting({
            id: "clhTool.translate.appid",
            name: "🟢 百度 translate appid 🔴",
            defaultValue: "",
            type: "text",
        });
        app.ui.settings.addSetting({
            id: "clhTool.translate.key",
            name: "🟢 百度 translate key 🔴",
            defaultValue: "",
            type: "password",
        });
        app.ui.settings.addSetting({
            id: "clhTool.zhipu.key",
            name: "🟢 智普Ai key 🔴",
            defaultValue: "",
            type: "password",
        });
    }
});
