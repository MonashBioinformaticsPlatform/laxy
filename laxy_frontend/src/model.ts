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

export class SampleSet extends UUIDModel {
    // [index: number]: Sample;

    public name: string;
    public items: Sample[] = [];

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
    public compute_resource: string;
    public exit_code: number | null;
    public remote_id: string;
    public params: any | null;
    public input_fileset_id: string;
    public output_fileset_id: string;
    public owner: number;
    public secret: string;
}
