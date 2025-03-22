/* eslint-disable */
<!--
  - coding=utf-8
  - Copyright 2021-present, the Recognai S.L. team.
  -
  - Licensed under the Apache License, Version 2.0 (the "License");
  - you may not use this file except in compliance with the License.
  - You may obtain a copy of the License at
  -
  -     http://www.apache.org/licenses/LICENSE-2.0
  -
  - Unless required by applicable law or agreed to in writing, software
  - distributed under the License is distributed on an "AS IS" BASIS,
  - WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  - See the License for the specific language governing permissions and
  - limitations under the License.
  -->

<template>
  <svg
    v-if="color === 'default'"
    width="420"
    height="420"
    viewBox="0 0 420 420"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <mask
      id="mask0_229_2069"
      style="mask-type:alpha"
      maskUnits="userSpaceOnUse"
      x="64"
      y="29"
      width="293"
      height="363"
    >
      <path
        d="M227.812 379.386C221.471 395.598 198.529 395.598 192.188 379.386L65.3328 55.0944C60.426 42.5508 69.676 29 83.1451 29L336.855 29C350.324 29 359.574 42.5508 354.668 55.0944L227.812 379.386Z"
        fill="url(#paint0_linear_229_2069)"
      />
    </mask>
    <g mask="url(#mask0_229_2069)">
      <path d="M56.4595 16.7709H366V122.017H56.4595V16.7709Z" fill="#FBF7F3" />
      <path d="M56.4597 138.704H366V243.951H56.4597V138.704Z" fill="#FBF7F3" />
      <path d="M56.4597 260.636H366V386.418H56.4597V260.636Z" fill="#FBF7F3" />
    </g>
    <defs>
      <linearGradient
        id="paint0_linear_229_2069"
        x1="210"
        y1="-102.974"
        x2="210"
        y2="424.921"
        gradientUnits="userSpaceOnUse"
      >
        <stop stop-color="#4C5FF4" />
        <stop offset="1" stop-color="#2C378E" />
      </linearGradient>
    </defs>
  </svg>
  <svg
    v-else-if="color === 'white'"
    width="420"
    height="420"
    viewBox="0 0 420 420"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <mask
      id="mask0_229_2069"
      style="mask-type:alpha"
      maskUnits="userSpaceOnUse"
      x="64"
      y="29"
      width="293"
      height="363"
    >
      <path
        d="M227.812 379.386C221.471 395.598 198.529 395.598 192.188 379.386L65.3328 55.0944C60.426 42.5508 69.676 29 83.1451 29L336.855 29C350.324 29 359.574 42.5508 354.668 55.0944L227.812 379.386Z"
        fill="white"
      />
    </mask>
    <g mask="url(#mask0_229_2069)">
      <path d="M56.4595 16.7709H366V122.017H56.4595V16.7709Z" fill="white" />
      <path d="M56.4597 138.704H366V243.951H56.4597V138.704Z" fill="white" />
      <path d="M56.4597 260.636H366V386.418H56.4597V260.636Z" fill="white" />
    </g>
  </svg>
</template>

<script>
export default {
  props: {
    color: {
      type: String,
      default: "default",
      validator: (value) => ["default", "white"].includes(value),
    },
  },
};
</script>
<style lang="scss" scoped></style>
