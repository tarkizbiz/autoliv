/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
const components = { Dialog };
import { patch } from "@web/core/utils/patch";

patch(components.Dialog.prototype, {

	setup(...args) {

    		super.setup(...args);    

    		var self = this;		
    		var message = this.props.message || '';
    		
            if (message.length) {

                //for auto close popup ends here
                //for play sound start here
                //if message has BARCODE_SCANNER_
                var str_msg = message.match("BARCODE_SCANNER_");
                if (str_msg) {
                    //remove BARCODE_SCANNER_ from message and make valid message
                    message = message.replace("BARCODE_SCANNER_", "");
                    //play sound
                    var src = "/pramadya_ekanban/static/src/sounds/error.wav";
                    $("body").append('<audio src="' + src + '" autoplay="true"></audio>');
                }
                //for play sound ends here
            }
            
            this.props.message = message;
            

    }
	
});