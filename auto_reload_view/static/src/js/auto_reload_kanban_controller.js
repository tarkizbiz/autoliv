/** @odoo-module */

import { useBus } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { patch } from "@web/core/utils/patch";
var worker_script = require('auto_reload_view.worker_timeout');
import { cookie } from "@web/core/browser/cookie";

const { onMounted, onWillDestroy } = owl;

patch(KanbanController.prototype, {
    setup() {
        super.setup();

        onMounted(this.onMounted);

        this.timerWorker = new Worker(worker_script);
        this.minute_reload = 0;

        var minute_reload = cookie.get('reload_' + this.env.config.viewId);
        if(minute_reload !== '' && !isNaN(minute_reload)){
            this.minute_reload = parseInt(minute_reload, 10);
        }

        onWillDestroy(() => {
           this.timerWorker.postMessage({ turn: "off" });
        });
    },

    onMounted() {
       $('body').on('click', 'i.fa-square-o:not(.custom-minute)', event => this._activateAutoReload(event));
       $('body').on('click', 'i.fa-check-square:not(.custom-minute)', event => this._deactivateAutoReload(event));

       $('body').on('click', 'i.fa-square-o.custom-minute', event => this._activateCustomMinuteAutoReload(event));
       $('body').on('click', 'i.fa-check-square.custom-minute', event => this._deactivateAutoReload(event));
       $('body').on('change', 'input.custom-minute', event => this._inputCustomMinuteAutoReload(event));

       var self = this;
       this.timerWorker.onmessage = ({ data: { time } }) => {
            self.checkInactiveSessionTimeout(time);
       };

       var minute_reload = cookie.get('reload_' + this.env.config.viewId);
       if(minute_reload !== '' && !isNaN(minute_reload)){
           this.minute_reload = parseInt(minute_reload, 10);
           this.timerWorker.postMessage({ turn: "on" });
       }
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    async checkInactiveSessionTimeout (time) {
        //console.log("secondCounter: " + time);
        if (this.minute_reload > 0 && time % (this.minute_reload * 60) == 0 && (this.model.root.editedRecord === undefined || this.model.root.editedRecord === null)){
            await this.model.load();
        }
    },

    _activateAutoReload (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();

        const $target = $(ev.currentTarget);

        this._updateCheckbox(ev);
        var minutes = $target.data("minute");

        if (minutes > 0) {
            this._startTimerWorker(minutes);
        }
    },

    _deactivateAutoReload (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();

        const $target = $(ev.currentTarget);
        $target.removeClass('fa-check-square').removeClass('text-primary');
        $target.addClass('fa-square-o');

        this._stopTimerWorker();
    },

    _activateCustomMinuteAutoReload (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        this._stopTimerWorker();

        const $target = $(ev.currentTarget);

        this._updateCheckbox (ev);
        const $input = $.find('input.custom-minute');
        if ($input.length == 1 && ($($input).val() === '' || $($input).val() == 0)){
            $($input).focus();
        }
        else if ($input.length == 1 && $($input).val() > 0) {
            this._startTimerWorker($input.val());
        }
    },

    _inputCustomMinuteAutoReload (ev) {
        const $target = $(ev.currentTarget);

        this._stopTimerWorker();
        if ($target.val() > 0) {
            this._startTimerWorker($target.val());
        }
    },

    _updateCheckbox (ev) {
        const $target = $(ev.currentTarget);
        const options = $target.closest('.auto-reload-options');

        options.find('i').each(function(index) {
            $(this).removeClass('fa-check-square').removeClass('text-primary');
            $(this).addClass('fa-square-o');
        });

        $target.removeClass('fa-square-o');
        $target.addClass('fa-check-square').addClass('text-primary');
    },

    _stopTimerWorker() {
        this.minute_reload = 0;
        cookie.set('reload_' + this.env.config.viewId, "", -1);
        this.timerWorker.postMessage({ turn: "off" });
    },

    _startTimerWorker(val) {
        this.minute_reload = val;
        cookie.set('reload_' + this.env.config.viewId, this.minute_reload);
        this.timerWorker.postMessage({ turn: "on" });
    },

});

