<template>
  <div class="import-demo">
    <h1>Import Analysis Table Demo</h1>

    <div class="demo-controls">
      <button @click="showDataframeData = !showDataframeData" class="toggle-btn">
        {{ showDataframeData ? 'Show Analysis Data' : 'Show Dataframe Data' }}
      </button>
      <button @click="toggleLoading" class="toggle-btn">
        {{ loading ? 'Stop Loading' : 'Start Loading' }}
      </button>
    </div>

    <ImportAnalysisTable
      :analysis-data="analysisData"
      :dataframe-data="showDataframeData ? dataframeData : null"
      :loading="loading"
      @update="handleUpdate"
      @retry="handleRetry"
    />

    <div v-if="lastUpdate" class="update-info">
      <h3>Last Update Event:</h3>
      <pre>{{ JSON.stringify(lastUpdate, null, 2) }}</pre>
    </div>
  </div>
</template>

<script>
export default {
  name: "ImportDemo",

  data() {
    return {
      loading: false,
      showDataframeData: true,
      lastUpdate: null,

      // Sample dataframe data (from BibTeX parsing)
      dataframeData: {
        schema: {
          fields: [
            { name: 'reference', type: 'string' },
            { name: 'title', type: 'string' },
            { name: 'authors', type: 'string' },
            { name: 'year', type: 'string' },
            { name: 'journal', type: 'string' },
          ],
          primaryKey: ['reference'],
        },
        data: [
          {
            reference: 'Smith2023',
            title: 'A Comprehensive Study on Machine Learning Applications in Healthcare',
            authors: 'John Smith, Jane Doe, Bob Johnson',
            year: '2023',
            journal: 'Journal of Medical AI',
          },
          {
            reference: 'Brown2024',
            title: 'Deep Learning for Natural Language Processing: Recent Advances',
            authors: 'Alice Brown, Charlie Wilson',
            year: '2024',
            journal: 'AI Research Quarterly',
          },
          {
            reference: 'Davis2022',
            title: 'Computer Vision in Autonomous Vehicles: Challenges and Solutions',
            authors: 'Emily Davis',
            year: '2022',
            journal: 'Robotics Today',
          },
          {
            reference: 'Wilson2023',
            title: 'Blockchain Technology and Its Applications in Supply Chain Management',
            authors: 'Michael Wilson, Sarah Lee, David Chen',
            year: '2023',
            journal: 'Technology Review',
          },
        ],
      },

      // Sample analysis data (from backend analysis)
      analysisData: {
        documents: {
          'Smith2023': {
            document_create: {
              title: 'A Comprehensive Study on Machine Learning Applications in Healthcare',
              authors: ['John Smith', 'Jane Doe', 'Bob Johnson'],
              year: '2023',
              journal: 'Journal of Medical AI',
            },
            associated_files: ['smith2023_healthcare_ml.pdf'],
            status: 'add',
            validation_errors: [],
          },
          'Brown2024': {
            document_create: {
              title: 'Deep Learning for Natural Language Processing: Recent Advances',
              authors: ['Alice Brown', 'Charlie Wilson'],
              year: '2024',
              journal: 'AI Research Quarterly',
            },
            associated_files: ['brown2024_nlp_advances.pdf', 'brown2024_supplementary.pdf'],
            status: 'update',
            validation_errors: [],
          },
          'Davis2022': {
            document_create: {
              title: 'Computer Vision in Autonomous Vehicles: Challenges and Solutions',
              authors: ['Emily Davis'],
              year: '2022',
              journal: 'Robotics Today',
            },
            associated_files: [],
            status: 'failed',
            validation_errors: ['No PDF file found'],
          },
        },
        summary: {
          total_documents: 3,
          add_count: 1,
          update_count: 1,
          skip_count: 0,
          failed_count: 1,
        },
      },
    };
  },

  methods: {
    toggleLoading() {
      this.loading = !this.loading;
    },

    handleUpdate(data) {
      console.log('Update event received:', data);
      this.lastUpdate = data;
    },

    handleRetry() {
      console.log('Retry event received');
      this.loading = true;
      setTimeout(() => {
        this.loading = false;
      }, 2000);
    },
  },
};
</script>

<style lang="scss" scoped>
.import-demo {
  padding: $base-space * 4;
  max-width: 1200px;
  margin: 0 auto;

  h1 {
    color: var(--fg-primary);
    margin-bottom: $base-space * 3;
  }

  .demo-controls {
    display: flex;
    gap: $base-space * 2;
    margin-bottom: $base-space * 3;

    .toggle-btn {
      padding: $base-space $base-space * 2;
      background: var(--bg-action);
      color: var(--fg-lighter);
      border: none;
      border-radius: $border-radius;
      cursor: pointer;
      font-size: $base-font-size;

      &:hover {
        background: var(--bg-action-accent);
      }
    }
  }

  .update-info {
    margin-top: $base-space * 3;
    padding: $base-space * 2;
    background: var(--bg-solid-grey-2);
    border-radius: $border-radius;

    h3 {
      margin: 0 0 $base-space 0;
      color: var(--fg-primary);
    }

    pre {
      background: var(--bg-accent-grey-1);
      padding: $base-space;
      border-radius: $border-radius-s;
      overflow-x: auto;
      font-size: 12px;
      color: var(--fg-primary);
    }
  }
}
</style>