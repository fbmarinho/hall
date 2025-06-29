const Tools = [
  {
    name: "HCIM",
    group: "busmaster",
    config: {
      battery: 96,
      download: Date.now(),
      delay: 0,
    },
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "BaseStar",
    group: "busmaster",
    battery: "96",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "DrillDOC",
    group: "optimization",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "PCD-C",
    group: "Direcional",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "PWD",
    group: "Pressure",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "PWD-M5",
    group: "Pressure",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "PWD-FTWD",
    group: "Pressure",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },

  {
    name: "AFR",
    group: "Resistivity",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "ADR",
    group: "Resistivity",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "EWR-P4",
    group: "Resistivity",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "EWR-P4D",
    group: "Resistivity",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "EWR-M5",
    group: "Resistivity",
    config: {},
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "DGR",
    group: "Gamma",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "AGR",
    group: "Gamma",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "ALD",
    group: "Density",
    battery: "24",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "BAT",
    group: "Porosity",
    battery: "96",
    config: {},
    drain: {
      from: "self",
      ammount: 50,
    },
  },
  {
    name: "XBAT",
    group: "Porosity",
    battery: "96",
    config: {},
    drain: {
      from: "self",
      ammount: 50,
    },
  },
  {
    name: "CTN",
    group: "Porosity",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "MRIL-WD",
    group: "Ressonance",
    battery: "12",
    config: {},
    drain: {
      from: "self",
      ammount: 50,
    },
  },
  {
    name: "DDSr-HCIM",
    group: "Vibration",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "DDSr-DGR",
    group: "Vibration",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "DDSr-DOC1",
    group: "Vibration",
    battery: "0",
    drain: {
      from: "subbus",
      ammount: 50,
    },
  },
  {
    name: "Jetpulse",
    group: "Telemetry",
    battery: "46",
    config: {},
    drain: {
      from: "self",
      ammount: 50,
    },
  },
  {
    name: "P4M",
    group: "Telemetry",
    battery: "0",
    config: {},
    drain: {
      from: "subbus",
      ammount: 0,
    },
  },
];

export default Tools;
