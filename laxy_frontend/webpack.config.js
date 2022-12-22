const path = require('path');
const webpack = require('webpack');
const UglifyJsPlugin = require("uglifyjs-webpack-plugin");
const VueLoaderPlugin = require('vue-loader/lib/plugin')
const WebpackShellPlugin = require('webpack-shell-plugin');
const Dotenv = require('dotenv-webpack');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const NyanProgressPlugin = require('nyan-progress-webpack-plugin');

const plugins = [
    new Dotenv({
        path: '../.env',
        safe: false, // load '.env.example' to verify the '.env' variables are all set. Can also be a string to a different file.
        systemvars: true, // load all the predefined 'process.env' variables which will override local dotenv specs.
        silent: false, // hide any errors
    }),
    // copy index.html to dist
    // new CopyWebpackPlugin([{
    //     from: './index.html'
    // }]),
    new HtmlWebpackPlugin({
        title: 'Laxy',
        filename: 'index.html',
        template: 'index.html',
        // favicon: 'assets/favicon.ico',
        hash: true,
    }),
    new VueLoaderPlugin(),
];

/*
plugins.push(new WebpackShellPlugin({
  // onBuildStart: ['echo "Starting"'],
  onBuildEnd: ['python3 ../manage.py collectstatic --no-input'],
  dev: false, // so that it always runs after rebuild in --watch mode
}));
*/

module.exports = {
    watch: false,
    entry: "./src/index.ts",
    output: {
        path: path.resolve(__dirname, './dist'),
        filename: process.env.NODE_ENV === 'production' ? "bundle.[hash].js" : "bundle.js",
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader',
                options: {},
            },
            {
                test: /\.tsx?$/,
                loader: 'ts-loader',
                exclude: /node_modules/,
                options: {
                    appendTsSuffixTo: [/\.vue$/],
                }
            },
            {
                test: /\.(png|jpg|gif|svg)$/,
                loader: 'file-loader',
                options: {
                    name: '[name].[ext]?[hash]',
                    outputPath: 'assets/',
                }
            },
            {
                test: /\.css$/,
                // loader: 'style-loader!css-loader',
                use: ['vue-style-loader', 'style-loader', 'css-loader']
            },
            {
                test: /\.scss$|\.sass$/,
                use: [
                    'vue-style-loader',
                    {
                        loader: 'css-loader',
                        options: { modules: true }
                    },
                    'sass-loader'
                ]
            }
        ]
    },
    resolve: {
        extensions: ['.ts', '.js', '.vue', '.json'],
        alias: {
            'vue$': 'vue/dist/vue.esm.js',
        }
    },
    plugins: plugins,
    devServer: {
        historyApiFallback: true,
        noInfo: true
    },
    performance: {
        hints: false
    },
    devtool: 'inline-source-map',
    optimization: {
        minimizer: [
            new UglifyJsPlugin({
                sourceMap: true,
                uglifyOptions: {}
            })
        ]
    },
};

if (process.env.NYAN === 'true') {
    module.exports.plugins = (module.exports.plugins || []).concat([
        new NyanProgressPlugin()
    ]);
}

// Return the JSONized value of an environment variable if it is truthy,
// otherwise return the default value
function get_env(envar, default_value) {
    const value = process.env[envar];
    return (value && JSON.stringify(value)) || JSON.stringify(default_value);
}

module.exports.plugins = (module.exports.plugins || []).concat([
    new webpack.DefinePlugin({
        'process.env': {
            // NODE_ENV is used in some dependencies and breaks things if replaced via webpack DefinePlugin pre-processing.
            // NODE_ENV: JSON.stringify(process.env.NODE_ENV) || JSON.stringify('production'),
            LAXY_ENV: JSON.stringify(process.env.LAXY_ENV) || JSON.stringify(process.env.NODE_ENV) || JSON.stringify('prod'),
            LAXY_FRONTEND_API_URL: get_env('LAXY_FRONTEND_API_URL', 'http://localhost:8001'),
            LAXY_FRONTEND_URL: get_env('LAXY_FRONTEND_URL', 'http://localhost:8002'),
            LAXY_FRONTEND_GOOGLE_OAUTH_CLIENT_ID: get_env('LAXY_FRONTEND_GOOGLE_OAUTH_CLIENT_ID', ''),
            LAXY_VERSION: get_env('GIT_COMMIT', 'unspecified'),
        }
    }),
]);

if (process.env.NODE_ENV === 'production') {
    module.exports.devtool = 'source-map';
    // http://vue-loader.vuejs.org/en/workflow/production.html
    module.exports.plugins = (module.exports.plugins || []).concat([
        new webpack.LoaderOptionsPlugin({
            minimize: true
        })
    ]);
}
