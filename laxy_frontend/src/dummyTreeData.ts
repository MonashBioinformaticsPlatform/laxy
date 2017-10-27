import { TreeNode, DataFile, FileSet } from './tree.ts';

const fileListOne: Array<DataFile> = [
    new DataFile({
        id: '1rgerhfkejwrbf1',
        name: 'ChookSample1_R1.fastq.gz',
        selected: false
    }),
    new DataFile({
        id: '2rgerhfkejwrbf2',
        name: 'ChookSample1_R2.fastq.gz',
        selected: false
    }),
    new DataFile({
        id: '3rgerhfkejwrbf3',
        name: 'ChookSample2_R1.fastq.gz',
        selected: false
    }),
    new DataFile({
        id: '4rgerhfkejwrbf4',
        name: 'ChookSample2_R2.fastq.gz',
        selected: false
    }),
];

const fileListTwo: Array<DataFile> = [
    new DataFile({id: '1sdfa', name: 'XYZZY_1.fastq.gz', selected: false}),
    new DataFile({id: '2dfgdfg', name: 'XYZZY_2.fastq.gz', selected: false}),

];

const fileListThree: Array<DataFile> = [
    new DataFile({id: '1sdfwdf', name: 'Sample3_C_rep1_R1.fastq.gz', selected: false}),
    new DataFile({id: '2dffdgds', name: 'Sample3_C_rep1_R2.fastq.gz', selected: false}),
    new DataFile({id: '3dfgsefg', name: 'Sample4_C_rep2_R1.fastq.gz', selected: false}),
    new DataFile({id: '4dfsfhsf', name: 'Sample4_C_rep2_R2.fastq.gz', selected: false}),
    new DataFile({id: '5dfgsefg', name: 'Sample5_T_rep1_R1.fastq.gz', selected: false}),
    new DataFile({id: '6dfsfhsf', name: 'Sample5_T_rep1_R2.fastq.gz', selected: false}),
    new DataFile({id: '7dffjefg', name: 'Sample5_T_rep2_R1.fastq.gz', selected: false}),
    new DataFile({id: '8dfsfhsf', name: 'Sample5_T_rep2_R2.fastq.gz', selected: false}),
];
const fileSetData: Array<FileSet> = [
    new FileSet("1dfbsegdfgvdrgasef", 'project', "Chicken Teeth RNAseq study", fileListOne),
    new FileSet("2gewrgsrtgstrgergesfw", 'project', "Single replicate Unicorn transcriptome", fileListTwo),
    new FileSet("3erwgresrtgsrtgwgwbt", 'project', "Sea Kelpie single cell", fileListThree),
];

const folderOne = new FileSet("4t4352435234523", 'folder', "This is a directory", fileListThree);
const nestedFileSet: FileSet = new FileSet('1124125325235', 'project', "Project Fileset Example");
nestedFileSet.children = fileSetData;
nestedFileSet.children.push(folderOne);

folderOne.children = fileListThree;

fileSetData[0].selected = true;
fileSetData[0].children.push(folderOne);

export { fileListOne, fileListTwo, fileListThree, fileSetData, folderOne, nestedFileSet };
