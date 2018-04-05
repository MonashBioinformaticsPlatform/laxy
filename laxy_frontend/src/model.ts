export class SampleSet {
    // [index: number]: Sample;

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

    public name: string;
    public items: Sample[] = [];

    // public get samples(): Sample[] {
    //     return this.items;
    // }
    // public set samples(s: Sample[]) {
    //     this.items = s;
    // }
}
