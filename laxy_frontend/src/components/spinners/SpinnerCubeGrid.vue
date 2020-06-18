<template>
  <div :style="cssProps">
    <div class="sk-cube-grid">
      <template v-for="n in numberOfCells">
        <div :class="'sk-cube sk-cube' + circularRange.next().value"></div>
      </template>
    </div>
  </div>
</template>

<script lang="ts">
/*
    Original from: https://github.com/tobiasahlin/SpinKit
    ----
    The MIT License (MIT)

    Copyright (c) 2015 Tobias Ahlin
    Copyright (c) 2018 Andrew Perry

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
    the Software, and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
    FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
    COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
    IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
    CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

import Vue, { ComponentOptions } from "vue";
import Component from "vue-class-component";

/*
From: https://github.com/alvaropinot/circular-iterator
*/
function* circularIterator(arr: any[]) {
  let index = -1;
  const elements = Array.isArray(arr) ? arr.slice() : [];
  const length = elements.length;

  while (length) {
    index = (index + 1) % length;
    yield elements[index];
  }
}

function* randomSample(arr: any[]) {
  yield arr[Math.floor(Math.random() * arr.length)];
}

@Component({
  props: {
    width: { type: Number, default: 40 },
    height: { type: Number, default: 40 },
    columns: { type: Number, default: 2 },
    rows: { type: Number, default: 2 },
    time: { type: Number, default: 1.3 },
    colors: { type: Array, default: ["black"] },
    randomSeed: { type: Number, default: 1 },
  }
})
export default class SpinnerCubeGrid extends Vue {

  public width: number;
  public height: number;
  public columns: number;
  public rows: number;
  public time: number;
  public colors: string[];
  public randomSeed: number;

  circularRange: IterableIterator<number>;

  created() {
    this.circularRange = this.rangeLoop(9);
  }

  get numberOfCells(): number {
    return this.rows * this.columns;
  }

  get cellWidth(): number {
    return this.width / this.columns;
  }

  get cellHeight(): number {
    return this.height / this.rows;
  }

  get gridPercentWidth(): number {
    return 100 / this.columns;
  }

  get gridPercentHeight(): number {
    return 100 / this.rows;
  }

  rangeLoop(n: number) {
    const array = Array.from({ length: n }, (v, k) => k + 1);
    return circularIterator(array);
  }

  get cssProps() {
    // const colorGenerator = circularIterator(this.colors);
    let seed = this.randomSeed;

    function badRandom() {
      const x = Math.sin(seed++) * 10000;
      return x - Math.floor(x);
    }

    function getRandom(arr: any[]) {
      return arr[Math.floor(badRandom() * arr.length)];
    }

    return {
      "--grid-width": `${this.width}px`,
      "--grid-height": `${this.height}px`,
      "--cell-width": `${this.cellWidth}px`,
      "--cell-height": `${this.cellHeight}px`,
      "--grid-percent-width": `${this.gridPercentWidth}%`,
      "--grid-percent-height": `${this.gridPercentHeight}%`,
      "--time": `${this.time}s`,
      "--colorA": `${getRandom(this.colors)}`,
      "--colorB": `${getRandom(this.colors)}`,
      "--colorC": `${getRandom(this.colors)}`,
      "--colorD": `${getRandom(this.colors)}`,
      "--colorE": `${getRandom(this.colors)}`,
      "--colorF": `${getRandom(this.colors)}`,
      "--colorG": `${getRandom(this.colors)}`,
      "--colorH": `${getRandom(this.colors)}`,
      "--colorI": `${getRandom(this.colors)}`,
    };
  }
}

</script>

<style scoped>
.sk-cube-grid {
  width: var(--grid-width);
  height: var(--grid-width);
  /* margin: 100px auto; */
}

.sk-cube-grid .sk-cube {
  width: var(--grid-percent-width);
  height: var(--grid-percent-height);
  background-color: black;
  border-radius: 25%;
  float: left;
  -webkit-animation: sk-cubeGridScaleDelay var(--time) infinite ease-in-out;
  animation: sk-cubeGridScaleDelay var(--time) infinite ease-in-out;
}

.sk-cube-grid .sk-cube1 {
  -webkit-animation-delay: 0.2s;
  animation-delay: 0.2s;
  background-color: var(--colorA);
}

.sk-cube-grid .sk-cube2 {
  -webkit-animation-delay: 0.3s;
  animation-delay: 0.3s;
  background-color: var(--colorB);
}

.sk-cube-grid .sk-cube3 {
  -webkit-animation-delay: 0.4s;
  animation-delay: 0.4s;
  background-color: var(--colorC);
}

.sk-cube-grid .sk-cube4 {
  -webkit-animation-delay: 0.1s;
  animation-delay: 0.1s;
  background-color: var(--colorD);
}

.sk-cube-grid .sk-cube5 {
  -webkit-animation-delay: 0.2s;
  animation-delay: 0.2s;
  background-color: var(--colorE);
}

.sk-cube-grid .sk-cube6 {
  -webkit-animation-delay: 0.3s;
  animation-delay: 0.3s;
  background-color: var(--colorF);
}

.sk-cube-grid .sk-cube7 {
  -webkit-animation-delay: 0s;
  animation-delay: 0s;
  background-color: var(--colorG);
}

.sk-cube-grid .sk-cube8 {
  -webkit-animation-delay: 0.1s;
  animation-delay: 0.1s;
  background-color: var(--colorH);
}

.sk-cube-grid .sk-cube9 {
  -webkit-animation-delay: 0.2s;
  animation-delay: 0.2s;
  background-color: var(--colorI);
}

@-webkit-keyframes sk-cubeGridScaleDelay {
  0%,
  70%,
  100% {
    -webkit-transform: scale3D(1, 1, 1);
    transform: scale3D(1, 1, 1);
  }
  35% {
    -webkit-transform: scale3D(0, 0, 1);
    transform: scale3D(0, 0, 1);
  }
}

@keyframes sk-cubeGridScaleDelay {
  0%,
  70%,
  100% {
    -webkit-transform: scale3D(1, 1, 1);
    transform: scale3D(1, 1, 1);
  }
  35% {
    -webkit-transform: scale3D(0, 0, 1);
    transform: scale3D(0, 0, 1);
  }
}
</style>
