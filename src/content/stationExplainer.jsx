// "About the station data" page (Step 2.7): what each number in the station
// tooltip means, how it was measured in the field, and how it was calculated.
//
// Sources for the numbers below: public/data/station_summary.json,
// public/data/site_summary.json, data-pipeline/reports/data_notes.md, the
// printed checks of data-pipeline/scripts/04_site_summary.py and
// 04b_station_summary.py, data-pipeline/species_lookup.csv, and the dataset
// metadata (raw/biocomplexity_2001_2004/BiocomplexityDR.xml). Recheck them if
// the pipeline changes.

export default function StationExplainer() {
  return (
    <>
      <p>
        TBD
      </p>
      {/* <p>
        When you pick a site, hovering one of its stations shows what was found there. This
        page explains each part of that tooltip: what it means, how it was measured in the
        field, and how it was calculated.
      </p>

      <h2>1. What the stations are</h2>
      <p>
        Each of the nine study sites is a grid of 45 <dfn>sampling stations</dfn> covering about
        1 km² of forest: 5 parallel <dfn>transects</dfn> (lines numbered 0, 200, 400, 600 and
        800, spaced 200 m apart), each with 9 stations (numbered 100 to 900, spaced 100 m apart).
        The sites run from near sea level (MAL, about 40 m) to about 1,800 m (SOL).
      </p>
      <p>
        Every station value is a <strong>total for all five survey seasons combined</strong>, May
        2002 to October 2004 (dry season May–October, wet season November–April). There is too
        little data at a single station to split it by season: on average about 13 trap nights,
        a handful of tested mosquitoes, and 2 bird counts per station per season.
      </p>
      <p>
        Station colors show <i>Culex</i> per trap night (section 4) on one scale shared by every
        site, so the same color means the same value everywhere. Grey means no data.
      </p>

      <h2>2. What <i>Culex</i> is, and why it matters</h2>
      <p>
        <i>Culex quinquefasciatus</i>, the <dfn>southern house mosquito</dfn>, is not native to
        Hawaiʻi; it arrived in the 1800s. It is the mosquito that carries <dfn>avian
        malaria</dfn> (the parasite <i>Plasmodium relictum</i>) from bird to bird in Hawaiʻi. The
        traps also caught <i>Aedes</i> and <i>Wyeomyia</i> mosquitoes, which don't carry avian
        malaria, so they aren't shown.
      </p>
      <p>
        Hawaiian honeycreepers evolved without this disease, and many die when infected. How
        much malaria spreads depends on both mosquitoes and temperature: below about 13°C the
        parasite can't finish developing inside the mosquito. That is why cool, high forests act
        as <dfn>refuges</dfn> where honeycreepers still thrive (LaPointe et al. 2010: above 21°C
        high risk, 13–21°C episodic, below 13°C refuge), and why the sites span such a wide range
        of elevation.
      </p>

      <h2>3. How mosquitoes were caught</h2>
      <p>The researchers used two kinds of trap:</p>
      <ul>
        <li>
          <strong>CO2 traps</strong>: light traps baited with about 300 g of dry ice and hung in
          trees 4–12 m up. The carbon dioxide imitates a breathing animal, so these traps catch
          females <em>looking for a blood meal</em>: the ones about to bite birds.
        </li>
        <li>
          <strong>Gravid traps</strong>: baited with alfalfa-infused water and set on the forest
          floor. They catch females <em>ready to lay eggs</em>, which have already fed on blood.
        </li>
      </ul>
      <p>
        Traps were set before sunset and emptied the next morning, on 4–9 nights per site per
        month. Mosquitoes were identified and counted in the field, and live <i>Culex</i> were
        taken to a lab. Nights when a trap was broken, disabled, or stolen were left out of the
        data.
      </p>
      <p>
        A <dfn>trap night</dfn> is one trap running for one night. It is the unit of trapping
        effort.
      </p>

      <h2>4. <i>Culex</i> per trap night</h2>
      <div className="formula">
        <i>Culex</i> per trap night = <i>Culex</i> caught ÷ number of trap nights
      </div>
      <p>
        This is a <dfn>rate</dfn> (catch per unit of effort), not a proportion, so it can be
        above 1. A value of 2 means a trap caught, on average, two <i>Culex</i> per night at that
        station. Zero means none were caught on any night (98 of the 405 stations). The highest
        station is about 4.65, which is why the color scale ends at “4+”.
      </p>
      <p>
        <strong>Why divide by trap nights?</strong> Stations weren't trapped equally often:
        between 27 and 99 trap nights each (about 62 on average). A station trapped twice as
        often would catch about twice as many mosquitoes even if mosquitoes were just as common
        there. Dividing by trap nights puts every station on the same footing.
      </p>
      <p>
        <strong>Why only CO2 traps?</strong> They catch the females that bite birds, and the two
        trap types catch at very different rates (CO2 traps averaged about 4.5 times the gravid
        catch, and the gap varies a lot by site). Mixing them would mix two different methods.
      </p>
      <p>
        <strong>The site-wide figure</strong> in the tooltip pools the whole site: every{' '}
        <i>Culex</i> caught at its 45 stations ÷ every trap night at those stations. Trap nights
        at different stations on the same night all count, because each is a separate trap
        catching different mosquitoes. That is why a site's total is far larger than the number
        of calendar days in the study: NAN, for example, has 2,823 trap nights from about 900
        days, roughly 63 per station.
      </p>
      <p className="note">
        It is a relative measure for comparing places, not a count of mosquitoes per area.
      </p>

      <h2>5. Mosquito infection: the gut and the salivary glands</h2>
      <h3>Which mosquitoes were tested</h3>
      <p>
        Only some of the <i>Culex</i> caught were tested: about 29% overall (5,306 of 18,309,
        from both trap types). The share varied from about 9% to 75% by month; it was highest
        when catches were small. The dataset doesn't say how mosquitoes were chosen for testing.
        Nobody could tell whether a mosquito was infected before testing it, so the choice
        couldn't have favored infected ones.
      </p>
      <p>
        Each tested mosquito was <dfn>dissected</dfn>: its gut and salivary glands were removed
        and examined under a microscope for the malaria parasite.
      </p>

      <h3>What the two tests mean</h3>
      <p>Inside a mosquito, the parasite develops in stages:</p>
      <ol>
        <li>The mosquito picks it up by feeding on an infected bird.</li>
        <li>Small cysts (<dfn>oocysts</dfn>) grow on the outside of its gut wall.</li>
        <li>The cysts burst and release <dfn>sporozoites</dfn>, which travel to the salivary glands.</li>
        <li>From then on, the mosquito can pass malaria to every bird it bites.</li>
      </ol>
      <table>
        <tbody>
          <tr>
            <th scope="row">Malaria in the gut</th>
            <td>
              The mosquito is <strong>infected</strong>: it has fed on an infected bird. It can't
              pass malaria on yet. This shows how much exposure mosquitoes get from infected birds.
            </td>
          </tr>
          <tr>
            <th scope="row">Malaria in the salivary glands</th>
            <td>
              The mosquito is <strong>infectious</strong>: it can pass malaria to birds when it
              bites. This is the better measure of risk to birds.
            </td>
          </tr>
        </tbody>
      </table>
      <p>
        A gut infection doesn't always reach the salivary glands. The mosquito may die first
        (wild <i>Culex</i> often live only a few weeks), it may be too cold for the parasite to
        develop, or the infection may fail and the cysts degenerate.
      </p>

      <h3>Why the two lines are shown separately</h3>
      <p>
        Most infected mosquitoes are positive in both places, but not all. Of the mosquitoes
        with both results, 500 were positive in both, 84 only in the gut (an early infection),
        and 82 only in the salivary glands (a later one, after the gut cysts had burst and
        disappeared). So a station can have more salivary-gland positives than gut positives,
        and the salivary line is not a subset of the gut line.
      </p>

      <h3>Why the number tested is usually the same on both lines</h3>
      <p>
        Both organs come from the same dissected mosquitoes, so “of 21” on one line is usually
        the same 21 on the other. They differ by a few when one organ's slide was missing or
        unreadable. Those results are left out, not counted as negative. Of 5,306 tested
        mosquitoes, 5,181 have both results, 55 have only a gut result, 30 have only a
        salivary-gland result, and 40 have neither.
      </p>

      <h3>Why counts instead of percentages</h3>
      <p>
        Most stations had only a few mosquitoes tested. A percentage like “33%” from 1 of 3
        looks more precise than it is, so the tooltip shows the counts. “No mosquitoes tested
        here” means none from that station were dissected, which is common at the high sites
        where almost none were caught. “Not tested” on one line means only the other test has
        results there.
      </p>

      <h3>Trap type affects infection</h3>
      <p>
        Unlike the per-trap-night figure, infection uses mosquitoes from both trap types, to keep
        the number tested up. Gravid-trap mosquitoes have already fed, so they test positive far
        more often: 31.6% had malaria in the salivary glands, against 7.8% from CO2 traps. A
        site's mix of trap types therefore affects its numbers. CRA is the clearest case: 75% of
        its tested mosquitoes came from gravid traps, which raises its overall rate, even though
        for each trap type on its own it matches nearby COO.
      </p>

      <h2>6. Bird counts</h2>
      <p>
        About every three months, an observer stood at each odd-numbered station (100, 300, 500,
        700 and 900; 25 per site) for an <dfn>8-minute count</dfn> and recorded every bird they
        saw or heard. Each visit is one <dfn>count</dfn>. Most of these stations had 10 counts
        over the five seasons (3 to 11).
      </p>
      <div className="formula">
        Birds per count = birds recorded ÷ number of counts (including counts with no birds)
      </div>
      <p>
        It is a relative measure for comparing places, not a population count: a bird can be
        recorded twice, and quiet or hidden birds are missed. Because the method is the same
        everywhere, a higher number means more birds. The site figure pools all of the site's
        counts in the same way as the <i>Culex</i> figure.
      </p>
      <ul>
        <li>
          <strong>Honeycreepers</strong>: the six Hawaiian honeycreepers in the data, ʻApapane,
          Hawaiʻi ʻAmakihi, ʻIʻiwi, Hawaiʻi ʻĀkepa, ʻAkiapōlāʻau, and Hawaiʻi Creeper (ʻAlawī).
          These are the birds most harmed by malaria.
        </li>
        <li>
          <strong>Non-native birds</strong>: every introduced species, such as the Warbling
          White-eye, Red-billed Leiothrix, Japanese Bush-warbler, House Finch, Northern Cardinal,
          and game birds like the Kalij Pheasant. Many introduced birds cope with malaria far
          better than honeycreepers.
        </li>
      </ul>
      <p>
        Other native birds (ʻŌmaʻo, Hawaiʻi ʻElepaio, and ʻIo) are in neither figure. Even-numbered
        stations had no bird counts, so their tooltips have no bird lines.
      </p>

      <h2>7. Reading a tooltip: an example</h2>
      <p>PUU, station 700 on transect 400, at about 1,300 m:</p>
      <div className="example">
        <div className="example__line"><i>Culex</i> per trap night: 4.544 (68 trap nights)</div>
        <div className="example__meaning">
          Over 68 nights of CO2 trapping, a trap here caught about 4.5 <i>Culex</i> a night.
        </div>
        <div className="example__line">Site-wide: 2.018 per trap night (2,962 trap nights across 45 stations)</div>
        <div className="example__meaning">
          Across all of PUU, about 2 a night, so this station had more than twice the site's rate.
        </div>
        <div className="example__line">Malaria in the gut: 5 of 50 mosquitoes</div>
        <div className="example__meaning">50 <i>Culex</i> from here were dissected; 5 were infected.</div>
        <div className="example__line">Malaria in the salivary glands: 4 of 49 mosquitoes</div>
        <div className="example__meaning">
          4 could pass malaria to birds. One mosquito's salivary-gland slide had no result, so 49.
        </div>
        <div className="example__line">Honeycreepers per count: 4 (10 counts)</div>
        <div className="example__meaning">About 4 honeycreepers recorded per 8-minute count; the site's figure is 3.76.</div>
        <div className="example__line">Non-native birds per count: 3.4 (10 counts)</div>
        <div className="example__meaning">About 3.4 introduced birds per count; the site's figure is 3.39.</div>
      </div>

      <h2>8. Limits to keep in mind</h2>
      <ul>
        <li>Station values are totals for all five seasons; they don't change with the season.</li>
        <li>Many stations have small samples, so a single mosquito or bird can change the picture.</li>
        <li>
          The dataset doesn't say how mosquitoes were chosen for testing, and the share tested
          varied by month, so busy months count for less in the infection totals than in the
          catch.
        </li>
        <li>Infection numbers depend partly on each site's mix of trap types.</li>
        <li>Bird figures are birds seen or heard per count, not numbers of individual birds.</li>
      </ul> */}
    </>
  )
}
