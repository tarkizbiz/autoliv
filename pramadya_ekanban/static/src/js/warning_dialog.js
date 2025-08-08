/** @odoo-module **/

import { WarningDialog } from "@web/core/errors/error_dialogs";

import { patch } from "@web/core/utils/patch";

const components = { WarningDialog };

patch(WarningDialog.prototype, {

	setup(...args) {

    		super.setup(...args);      

    		var self = this;		
		
            if (self.message.length) {
                //for auto close popup ends here
                //for play sound start here
                //if message has BARCODE_SCANNER_
                var str_msg = self.message.match("BARCODE_SCANNER_");
                if (str_msg) {
                    //remove BARCODE_SCANNER_ from message and make valid message
                    self.message = self.message.replace("BARCODE_SCANNER_", "");
                    //play sound
                    var src = "/pramadya_ekanban/static/src/sounds/error.wav";
                    $("body").append('<audio src="' + src + '" autoplay="true"></audio>');
                }
                //for play sound ends here
            }
  
    }
		
	
});