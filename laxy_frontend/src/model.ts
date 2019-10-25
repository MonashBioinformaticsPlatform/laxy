class UUIDModel {
    // public id: string | undefined;
    private _id?: string;
    public get id(): (string | undefined) {
        return this._id;
    }

    // id should be effectively immutable after being set once
    public set id(i: string | undefined) {
        if (this._id == null && i !== undefined) {
            this._id = i;
        }
    }
}

export class Sample implements ISample {
    public id?: string;
    public name: string;
    public files: PairedEndFiles[];
    public metadata: {}; // {condition: '', ena: {}}
    // condition?: string;

    constructor(obj: any) {
        this.id = obj.id;
        this.name = obj.name;
        this.files = obj.files || [];
        this.metadata = obj.metadata || {};
    }
}

export class SampleCartItems extends UUIDModel {
    // [index: number]: Sample;

    public name: string;
    public items: ISample[] = [];

    // public get samples(): Sample[] {
    //     return this.items;
    // }
    // public set samples(s: Sample[]) {
    //     this.items = s;
    // }
}

export class ComputeJob extends UUIDModel {
    public status: string;
    public latest_event: string;
    public created_time: Date | null;
    public modified_time: Date | null;
    public completed_time: Date | null;
    public expiry_time: Date | null;
    public expired: boolean;
    public compute_resource: string;
    public exit_code: number | null;
    public remote_id: string;
    public params: any | null;
    public metadata: any | null;
    public input_fileset_id: string;
    public output_fileset_id: string;
    public owner: string;
    public secret: string;
}

export class LaxyFile implements ILaxyFile {
    public id: string;
    public name: string;
    public path: string;
    public location: string;
    public owner: number | string;
    public checksum: string | null;
    public fileset: string | null;
    public metadata: any;
    public type_tags: string[];
    public deleted: boolean;
}
