import { ComfyWidgets } from "../../../scripts/widgets.js";
import { app } from "../../../scripts/app.js";
/**
    流动样式
*/
export class RenderAllUeLinks {


    static queue_size = null;
    static note_queue_size(x) { this.queue_size = x; }
    static render_all_ue_links(ctx) {
        try {
            this._render_all_ue_links(ctx);
        } catch (e) {
            console.error(e);
        }
    }

    static _render_all_ue_links(ctx) {

        ctx.save();
        const orig_hqr = app.canvas.highquality_render;
        app.canvas.highquality_render = false;
        var mode = 4
        var animate = app.ui.settings.getSettingValue('clhTool.links.animateType', 1);
        if (app.ui.settings.getSettingValue('AE.stop.animation.running', true) && this.queue_size>0) animate = 0;
        if (animate==2 || animate==3) this.animate_step(ctx);
        //动态模糊
//        this.animate_step(ctx);
        var any_links_shown = false;
        var any_links = false;

        app.canvas.graph.links.forEach((ue_connection) => {
            any_links = true;
            var show = app.ui.settings.getSettingValue('clhTool.links.animate', false);

            if ( show ) {
                this._render_ue_link(ue_connection, ctx, animate);
                any_links_shown = true;
            }
        });

        
        if (animate>0) {
            /*
            If animating, we want to mark the visuals as changed so the animation updates - but not often!
            If links shown:
              - If showing dots, wait 30ms
              - Otherwise, wait 100ms
            If no links are shown
              - If there are links, and our mode is mouseover, wait 200ms
              - Otherwise don't request an update (there are no links that could be shown without something else requesting a redraw)
            */
//            const timeout = (any_links_shown) ? ((animate % 2 == 1) ? 100 : 100) : ((mode==2 || mode==3) && any_links) ? 200 : -1;
//            const timeout = 300;
//            if (timeout>0) setTimeout( app.graph.change.bind(app.graph), timeout );
            //防止多次注册
            if(!this.registered){
                this.registered = true;
                this.setLinkTimeout(ctx);
            }
        }

        app.canvas.highquality_render = orig_hqr;
        ctx.restore();
        this.reading_list = false;
    }
    static registered = false;
    //定时刷新
    static setLinkTimeout(ctx){
            const timeout = app.ui.settings.getSettingValue('clhTool.links.animateTime', 1000);
            if (timeout>0) setTimeout( ()=>{
                var animate = app.ui.settings.getSettingValue('clhTool.links.animateType', 1);
                if(animate){
//                    this.render_all_ue_links(app.canvas.ctx)
                    app.graph.change.bind(app.graph)();
                    this.setLinkTimeout(ctx);
                }
            }, timeout );

    }

    // memory reuse
    static slot_pos1 = new Float32Array(2); //to reuse
    static slot_pos2 = new Float32Array(2); //to reuse
    static _render_ue_link(ue_connection, ctx, animate) {
        try {
//            const node = get_real_node(ue_connection.sending_to.id);
            const start_node = app.canvas.graph.getNodeById(ue_connection.origin_id)
            const target_node = app.canvas.graph.getNodeById(ue_connection.target_id)
            /* this is the end node; get the position of the input */
            const pos1 = start_node.getConnectionPos(false, ue_connection.origin_slot, this.slot_pos2);
            var pos2 = target_node.getConnectionPos(true, ue_connection.target_slot, this.slot_pos1);

            // todo 计算方向
            var start_slot = start_node.outputs[ue_connection.origin_slot];
            var end_slot = target_node.inputs[ue_connection.target_slot];
            if (!start_slot || !end_slot) {
              return;
            }
            var start_dir = start_slot.dir || (start_node.horizontal ? LiteGraph.DOWN : LiteGraph.RIGHT);
            var end_dir = end_slot.dir || (target_node.horizontal ? LiteGraph.UP : LiteGraph.LEFT);

            var color = LGraphCanvas.link_type_colors[ue_connection.type];
            if (color=="") color = app.canvas.default_link_color;
            ctx.shadowColor = color;
            
//            app.canvas.renderLink(ctx, pos1, pos2, ue_connection, false, 0, color, sta_direction, end_direction, 1);

            this.animate_point(ctx, pos1, pos2, ue_connection, false, 0, color, start_dir, end_dir, 0)
        } catch (e) {
            console.log( `Couldn't render flow link ${ue_connection}. That's ok if something just got deleted.{e}`);
        }
    }

   static animate_step(ctx) {
        const max_blur = 18;
        const speed = 0.5;
        var f = (LiteGraph.getTime() * 0.001 * speed) % 1;
        const step = Math.ceil(f * 2 * max_blur) % (2 * max_blur);
        ctx.shadowBlur = (step < max_blur) ? step + 4 : 3 + 2 * max_blur - step;
   }
   static animate_point(ctx, a, b, link, skip_border, flow, color, start_dir, end_dir, num_sublines){

//            var color = LGraphCanvas.link_type_colors[ue_connection.type];
//            if (color=="") color = app.canvas.default_link_color;
          ctx.fillStyle = color;
          //点个数
          var max_count = 1;
          //循环周期 ，单位：秒
          var cycle_period = 5
          for (var i2 = 0; i2 < max_count; ++i2) {
            //计算第i个点的位置百分百 根据当前时间计算第一个点位置，再加上后面点的偏移，就可知道当前点的位置
            var f = (LiteGraph.getTime() * 1e-3 /cycle_period + i2 * 1.0 /max_count) % 1;
            var pos2 = app.canvas.computeConnectionPoint(
              a,
              b,
              f,
              start_dir,
              end_dir
            );
            ctx.beginPath();
            ctx.arc(pos2[0], pos2[1], 5, 0, 2 * Math.PI);
            ctx.fill();
          }

   }
}
//export{RenderAllUeLinks}
//export {displayMessage, update_input_label, nodes_in_my_group, nodes_not_in_my_group, nodes_in_groups_matching, nodes_my_color, nodes_not_my_color, indicate_restriction}
//export{ LinkRenderController}