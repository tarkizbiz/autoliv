/* @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class KanbancardModel extends RelationalModel {
    static DEFAULT_OPEN_GROUP_LIMIT = 20;
    static MAX_NUMBER_OPENED_GROUPS = 20;

}