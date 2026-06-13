<template>
  <span> {{ formattedDate }} </span>
</template>

<script>
export default {
  props: {
    date: {
      type: String,
      required: true,
    },
    format: {
      type: String,
    },
    updateEverySecond: {
      type: Number,
    },
  },
  data() {
    return {
      formattedDate: null,
      timer: null,
    };
  },
  beforeMount() {
    this.formatDate();
  },
  mounted() {
    const self = this;
    const reRender = () => {
      if (this.timer) clearTimeout(this.timer);
      this.timer = setTimeout(() => {
        this.$nextTick(() => self.formatDate());
        reRender();
      }, this.updateEverySecond * 1000);
    };

    if (this.updateEverySecond) {
      reRender();
    }
  },
  unmounted() {
    if (this.timer) clearTimeout(this.timer);
  },
  methods: {
    formatDate() {
      const date = new Date(this.date);

      if (this.format === "date-relative-now") {
        this.formattedDate = this.timeAgo(date);
        return;
      } else if (this.format === "date-local") {
        const utcDate = this.date.endsWith("Z") ? this.date : `${this.date}Z`;
        this.formattedDate = new Date(utcDate).toLocaleString(undefined, {
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
        return;
      }

      this.formattedDate = date.toLocaleString("sv", {
        year: "numeric",
        month: "numeric",
        day: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: false,
      });
    },
    timeAgo(date) {
      const formatter = new Intl.RelativeTimeFormat(this.$i18n.locale, {
        numeric: "auto",
      });
      const ranges = {
        years: 3600 * 24 * 365,
        months: 3600 * 24 * 30,
        weeks: 3600 * 24 * 7,
        days: 3600 * 24,
        hours: 3600,
        minutes: 60,
        seconds: 1,
      };

      const now = new Date();
      const time = new Date(date.getTime() - now.getTime());
      time.setMinutes(time.getMinutes() - now.getTimezoneOffset());

      const secondsElapsed = time / 1000;
      for (const key in ranges) {
        if (ranges[key] <= Math.abs(secondsElapsed)) {
          const delta = secondsElapsed / ranges[key];
          return formatter.format(Math.round(delta), key);
        }
      }

      return formatter.format(0, "seconds");
    },
  },
};
</script>
